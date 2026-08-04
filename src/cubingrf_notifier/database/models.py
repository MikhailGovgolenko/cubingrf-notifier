from typing import List
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    notifications = relationship("Notification", back_populates="user")

class Competition(Base):
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True)
    external_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(512), nullable=False)
    location = Column(String(255), nullable=True)
    date = Column(String(128), nullable=True)
    url = Column(String(1024), nullable=True)
    disciplines = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    notifications = relationship("Notification", back_populates="competition")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
    competition = relationship("Competition", back_populates="notifications")
