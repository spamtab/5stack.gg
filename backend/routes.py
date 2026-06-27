from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified
from typing import List

from database import get_db
import models
import schemas
import auth

router = APIRouter()

# @router.get("/users/me", response_model=schemas.UserResponse)
# async def read_users_me(current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(models.User).where(models.User.id == current_user_id))
#     user = result.scalars().first()
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user

@router.get("/users/me")
async def read_users_me(
    current_user_id: str = Depends(auth.get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    print("Firebase UID:", current_user_id)

    result = await db.execute(
        select(models.User).where(
            models.User.id == current_user_id
        )
    )

    user = result.scalars().first()

    print("Database user:", user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user

@router.post("/users", response_model=schemas.UserResponse)
async def create_user(user_in: schemas.UserCreate, current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.id == current_user_id))
    db_user = result.scalars().first()
    
    if db_user:
        # Update existing user preferences/username
        if user_in.username is not None:
            db_user.username = user_in.username
        if user_in.rank is not None:
            db_user.rank = user_in.rank
        if user_in.agent_priority is not None:
            # Assign a fresh list copy — JSON columns need flag_modified
            # so SQLAlchemy reliably detects the change and commits it.
            db_user.agent_priority = list(user_in.agent_priority)
            flag_modified(db_user, 'agent_priority')
        if user_in.mood is not None:
            db_user.mood = user_in.mood
        if user_in.looking_for_party is not None:
            db_user.looking_for_party = user_in.looking_for_party
    else:
        # Create new user
        db_user = models.User(
            id=current_user_id,
            username=user_in.username,
            rank=user_in.rank,
            agent_priority=user_in.agent_priority,
            mood=user_in.mood,
            looking_for_party=user_in.looking_for_party if user_in.looking_for_party is not None else False,
        )
        db.add(db_user)
        
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/users", response_model=List[schemas.UserResponse])
async def list_users(current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    # Returns users who are NOT in a party (individual player view)
    # Exclude the logged-in user from the public roster.
    result = await db.execute(
        select(models.User).where(
            models.User.party_id == None,
            models.User.looking_for_party == True,
            models.User.id != current_user_id,
        )
    )
    return result.scalars().all()

@router.post("/parties", response_model=schemas.PartyResponse)
async def create_party(party_in: schemas.PartyCreate, current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    if not party_in.code or not party_in.code.strip():
        raise HTTPException(status_code=400, detail="Party code is required")

    # Check if user is already in a party
    result = await db.execute(select(models.User).where(models.User.id == current_user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.party_id is not None:
        raise HTTPException(status_code=400, detail="User is already in a party")
        
    db_party = models.Party(
        leader_id=current_user_id,
        code=party_in.code
    )
    db.add(db_party)
    await db.commit()
    await db.refresh(db_party)
    
    # Add leader to the party members
    user.party_id = db_party.id
    await db.commit()
    await db.refresh(db_party) # refresh to load members (lazy might need eager loading, but we will just return)
    
    return db_party

@router.get("/parties", response_model=List[schemas.PartyResponse])
async def list_parties(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    stale_result = await db.execute(select(models.Party).where(models.Party.code == None))
    stale_parties = stale_result.scalars().all()
    for stale_party in stale_parties:
        members_result = await db.execute(select(models.User).where(models.User.party_id == stale_party.id))
        members = members_result.scalars().all()
        for member in members:
          member.party_id = None

        request_result = await db.execute(select(models.PartyRequest).where(models.PartyRequest.party_id == stale_party.id))
        requests = request_result.scalars().all()
        for request in requests:
            await db.delete(request)

        await db.delete(stale_party)

    if stale_parties:
        await db.commit()

    result = await db.execute(
        select(models.Party)
        .where(models.Party.code != None)
        .options(selectinload(models.Party.members))
    )
    return result.scalars().all()

@router.get("/parties/me", response_model=schemas.PartyResponse)
async def get_my_party(current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    stale_result = await db.execute(select(models.Party).where(models.Party.code == None))
    stale_parties = stale_result.scalars().all()
    for stale_party in stale_parties:
        members_result = await db.execute(select(models.User).where(models.User.party_id == stale_party.id))
        members = members_result.scalars().all()
        for member in members:
            member.party_id = None

        request_result = await db.execute(select(models.PartyRequest).where(models.PartyRequest.party_id == stale_party.id))
        requests = request_result.scalars().all()
        for request in requests:
            await db.delete(request)

        await db.delete(stale_party)

    if stale_parties:
        await db.commit()

    user_result = await db.execute(select(models.User).where(models.User.id == current_user_id))
    user = user_result.scalars().first()
    if not user or not user.party_id:
        raise HTTPException(status_code=404, detail="Party not found")

    party_result = await db.execute(
        select(models.Party)
        .options(selectinload(models.Party.members))
        .where(models.Party.id == user.party_id)
    )
    party = party_result.scalars().first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    return party

@router.delete("/parties/leave")
async def leave_party(current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.id == current_user_id))
    user = result.scalars().first()
    if not user or not user.party_id:
        raise HTTPException(status_code=400, detail="User is not in a party")

    party_result = await db.execute(select(models.Party).where(models.Party.id == user.party_id))
    party = party_result.scalars().first()
    if party and party.leader_id == current_user_id:
        members_result = await db.execute(select(models.User).where(models.User.party_id == party.id))
        members = members_result.scalars().all()
        for member in members:
            member.party_id = None

        requests_result = await db.execute(select(models.PartyRequest).where(models.PartyRequest.party_id == party.id))
        requests = requests_result.scalars().all()
        for request in requests:
            await db.delete(request)

        await db.delete(party)
        await db.commit()
        return {"message": "Party disbanded successfully"}
    
    party_id = user.party_id
    user.party_id = None
    
    # Check if party is now empty, if so delete it
    party_result = await db.execute(select(models.Party).where(models.Party.id == party_id))
    party = party_result.scalars().first()
    
    await db.commit()
    
    # If leader leaves, and there are others, we should probably reassign leader or disband. 
    # For now, just disband if empty.
    if party:
        members_result = await db.execute(select(models.User).where(models.User.party_id == party_id))
        members = members_result.scalars().all()
        if not members:
            await db.delete(party)
            await db.commit()
            
    return {"message": "Left party successfully"}

@router.delete("/parties/members/{member_id}")
async def remove_party_member(member_id: str, current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    leader_result = await db.execute(select(models.User).where(models.User.id == current_user_id))
    leader = leader_result.scalars().first()
    if not leader or not leader.party_id:
        raise HTTPException(status_code=400, detail="User is not in a party")

    party_result = await db.execute(select(models.Party).where(models.Party.id == leader.party_id))
    party = party_result.scalars().first()
    if not party or party.leader_id != current_user_id:
        raise HTTPException(status_code=403, detail="Only the party leader can remove members")

    member_result = await db.execute(select(models.User).where(models.User.id == member_id))
    member = member_result.scalars().first()
    if not member or member.party_id != party.id:
        raise HTTPException(status_code=404, detail="Party member not found")

    if member.id == party.leader_id:
        raise HTTPException(status_code=400, detail="Leader cannot be removed here")

    member.party_id = None

    await db.commit()

    remaining_result = await db.execute(select(models.User).where(models.User.party_id == party.id))
    remaining_members = remaining_result.scalars().all()
    if not remaining_members:
        await db.delete(party)
        await db.commit()

    return {"message": "Party member removed successfully"}

@router.delete("/parties/disband")
async def disband_party(current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.id == current_user_id))
    user = result.scalars().first()
    if not user or not user.party_id:
        raise HTTPException(status_code=400, detail="User is not in a party")

    party_id = user.party_id

    party_result = await db.execute(select(models.Party).where(models.Party.id == party_id))
    party = party_result.scalars().first()
    if not party:
        user.party_id = None
        await db.commit()
        return {"message": "Party already removed"}

    members_result = await db.execute(select(models.User).where(models.User.party_id == party_id))
    members = members_result.scalars().all()
    for member in members:
        member.party_id = None

    requests_result = await db.execute(select(models.PartyRequest).where(models.PartyRequest.party_id == party_id))
    requests = requests_result.scalars().all()
    for request in requests:
        await db.delete(request)

    await db.delete(party)
    await db.commit()

    return {"message": "Party disbanded successfully"}

@router.post("/requests", response_model=schemas.PartyRequestResponse)
async def create_request(request_in: schemas.PartyRequestCreate, current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    db_request = models.PartyRequest(
        type=request_in.type,
        sender_id=current_user_id,
        receiver_id=request_in.receiver_id,
        party_id=request_in.party_id
    )
    db.add(db_request)
    await db.commit()
    await db.refresh(db_request)
    # TODO: send websocket notification to receiver
    return db_request

@router.get("/requests/incoming", response_model=List[schemas.PartyRequestResponse])
async def get_incoming_requests(current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    # If user is in a party and is leader, show JOIN requests for that party
    user_result = await db.execute(select(models.User).where(models.User.id == current_user_id))
    user = user_result.scalars().first()
    
    requests = []
    if user and user.party_id:
        party_result = await db.execute(select(models.Party).where(models.Party.id == user.party_id))
        party = party_result.scalars().first()
        if party and party.leader_id == current_user_id:
            res = await db.execute(select(models.PartyRequest).where(models.PartyRequest.party_id == party.id, models.PartyRequest.status == models.RequestStatus.PENDING).options(selectinload(models.PartyRequest.sender)))
            requests.extend(res.scalars().all())
    
    # Also show INVITE requests where user is the receiver
    res2 = await db.execute(select(models.PartyRequest).where(models.PartyRequest.receiver_id == current_user_id, models.PartyRequest.status == models.RequestStatus.PENDING).options(selectinload(models.PartyRequest.sender)))
    requests.extend(res2.scalars().all())
    
    return requests

@router.post("/requests/{request_id}/respond")
async def respond_to_request(request_id: int, accept: bool, current_user_id: str = Depends(auth.get_current_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.PartyRequest).where(models.PartyRequest.id == request_id))
    db_request = result.scalars().first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
        
    db_request.status = models.RequestStatus.ACCEPTED if accept else models.RequestStatus.REJECTED
    
    if accept:
        if db_request.type == models.RequestType.JOIN:
            # Add sender to party
            sender_res = await db.execute(select(models.User).where(models.User.id == db_request.sender_id))
            sender = sender_res.scalars().first()
            if sender:
                sender.party_id = db_request.party_id
        elif db_request.type == models.RequestType.INVITE:
            # Add receiver to sender's party
            receiver_res = await db.execute(select(models.User).where(models.User.id == db_request.receiver_id))
            receiver = receiver_res.scalars().first()
            if receiver:
                sender_res = await db.execute(select(models.User).where(models.User.id == db_request.sender_id))
                sender = sender_res.scalars().first()
                if sender and sender.party_id:
                    receiver.party_id = sender.party_id
                
    await db.commit()
    # TODO: send websocket notification to other party
    return {"message": "Request processed"}
