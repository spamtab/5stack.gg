from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MoodEnum(str, Enum):
    SERIOUS = "serious locked in"
    CHILL = "chill competitive"

class RequestType(str, Enum):
    JOIN = "join"
    INVITE = "invite"

class RequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class UserBase(BaseModel):
    username: Optional[str] = None
    rank: Optional[str] = None
    agent_priority: Optional[List[str]] = None
    mood: Optional[MoodEnum] = None
    looking_for_party: Optional[bool] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: str
    party_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class PartyBase(BaseModel):
    code: str

class PartyCreate(PartyBase):
    pass

class PartyResponse(PartyBase):
    id: int
    leader_id: str
    created_at: datetime
    members: List[UserResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class PartyRequestBase(BaseModel):
    type: RequestType
    receiver_id: Optional[str] = None
    party_id: Optional[int] = None

class PartyRequestCreate(PartyRequestBase):
    pass

class PartyRequestResponse(PartyRequestBase):
    id: int
    sender_id: str
    status: RequestStatus
    created_at: datetime
    
    sender: Optional[UserResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
