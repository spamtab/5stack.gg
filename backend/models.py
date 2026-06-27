from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Enum, DateTime, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class MoodEnum(str, enum.Enum):
    SERIOUS = "serious locked in"
    CHILL = "chill competitive"

class RequestType(str, enum.Enum):
    JOIN = "join"
    INVITE = "invite"

class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # Firebase uid
    username = Column(String, unique=True, index=True, nullable=True) # username#tagline
    
    # Preferences
    rank = Column(String, nullable=True)
    agent_priority = Column(JSON, nullable=True) # List of agent names
    mood = Column(Enum(MoodEnum), nullable=True)
    looking_for_party = Column(Boolean, nullable=False, default=False, server_default="false")
    
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    
    # Relationships
    party = relationship("Party", back_populates="members", foreign_keys=[party_id])
    parties_led = relationship("Party", back_populates="leader", foreign_keys="Party.leader_id")
    
    # Requests where user is the sender
    sent_requests = relationship("PartyRequest", back_populates="sender", foreign_keys="PartyRequest.sender_id")
    # Requests where user is the receiver (for invites)
    received_invites = relationship("PartyRequest", back_populates="receiver", foreign_keys="PartyRequest.receiver_id")

class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    leader_id = Column(String, ForeignKey("users.id"), nullable=False)
    code = Column(String, nullable=True) # User-entered party code
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    leader = relationship("User", back_populates="parties_led", foreign_keys=[leader_id])
    members = relationship("User", back_populates="party", foreign_keys="User.party_id")
    
    join_requests = relationship("PartyRequest", back_populates="party", foreign_keys="PartyRequest.party_id")

class PartyRequest(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(RequestType), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(String, ForeignKey("users.id"), nullable=True) # For invites
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True) # For joins
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    sender = relationship("User", back_populates="sent_requests", foreign_keys=[sender_id])
    receiver = relationship("User", back_populates="received_invites", foreign_keys=[receiver_id])
    party = relationship("Party", back_populates="join_requests", foreign_keys=[party_id])
