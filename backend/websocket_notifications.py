"""
WebSocket notification helpers for sending real-time updates to clients.
"""
from typing import Optional, Dict, Any


async def notify_request_created(
    manager,
    request_id: int,
    request_type: str,
    sender_data: Dict[str, Any],
    receiver_id: Optional[str] = None,
    party_id: Optional[int] = None
):
    """
    Notify recipient(s) of a new request.
    - For JOIN requests: notify party leader
    - For INVITE requests: notify receiver
    """
    message = {
        "type": "request_created",
        "data": {
            "id": request_id,
            "type": request_type,
            "sender": sender_data,
            "party_id": party_id,
        }
    }
    
    if receiver_id:
        await manager.send_personal_message(message, receiver_id)


async def notify_request_responded(
    manager,
    request_id: int,
    status: str,
    request_type: str,
    sender_id: str
):
    """
    Notify sender that their request was accepted/rejected.
    """
    message = {
        "type": "request_responded",
        "data": {
            "id": request_id,
            "status": status,
            "request_type": request_type
        }
    }
    
    await manager.send_personal_message(message, sender_id)


async def notify_party_member_added(
    manager,
    party_id: int,
    member_data: Dict[str, Any]
):
    """
    Notify all party members that a new member joined.
    """
    message = {
        "type": "party_member_added",
        "data": {
            "party_id": party_id,
            "member": member_data
        }
    }
    
    await manager.send_to_party(message, party_id)


async def notify_party_member_removed(
    manager,
    party_id: int,
    member_id: str,
    reason: str = "left"
):
    """
    Notify party members that someone left/was kicked.
    Also notify the removed member.
    """
    message = {
        "type": "party_member_removed",
        "data": {
            "party_id": party_id,
            "member_id": member_id,
            "reason": reason
        }
    }
    
    # Notify the party
    await manager.send_to_party(message, party_id)
    
    # Also notify the removed member
    await manager.send_personal_message(message, member_id)


async def notify_party_disbanded(
    manager,
    party_id: int
):
    """
    Notify all party members that the party was disbanded.
    """
    message = {
        "type": "party_disbanded",
        "data": {
            "party_id": party_id
        }
    }
    
    await manager.send_to_party(message, party_id)


async def notify_player_status_changed(
    manager,
    user_id: str,
    looking_for_party: bool
):
    """
    Broadcast to all connected users that a player's status changed.
    """
    message = {
        "type": "player_status_changed",
        "data": {
            "user_id": user_id,
            "looking_for_party": looking_for_party
        }
    }
    
    # Broadcast to all connected users
    await manager.broadcast(message)
