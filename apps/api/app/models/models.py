from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Numeric, BigInteger
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    registration_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_interaction = Column(DateTime)
    lastname = Column(String(255))
    first_name = Column(String(255))
    phone = Column(String(20))
    country = Column(String(255))
    username = Column(String(255))
    bio = Column(Text)

    training_records = relationship("Training", back_populates="user")

class Muscle(Base):
    __tablename__ = "muscles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    is_global = Column(Boolean, default=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    exercises = relationship("Exercise", back_populates="muscle_group")
    training_records = relationship("Training", back_populates="muscle_group")

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    muscle = Column(Integer, ForeignKey("muscles.id"))
    is_global = Column(Boolean, default=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    muscle_group = relationship("Muscle", back_populates="exercises")
    exercise_records = relationship("Training", back_populates="exercise")

class Training(Base):
    __tablename__ = "training"

    id = Column(String(32), primary_key=True)
    date = Column(DateTime, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    muscle_id = Column(Integer, ForeignKey("muscles.id"))
    exercise_id = Column(Integer, ForeignKey("exercises.id"))
    set = Column(Integer)
    weight = Column(Numeric(5, 2))
    reps = Column(Numeric(5, 2))

    user = relationship("User", back_populates="training_records")
    muscle_group = relationship("Muscle", back_populates="training_records")
    exercise = relationship("Exercise", back_populates="exercise_records")

class UserHiddenMuscle(Base):
    __tablename__ = "user_hidden_muscles"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    muscle_id = Column(Integer, ForeignKey("muscles.id"), primary_key=True)

class UserHiddenExercise(Base):
    __tablename__ = "user_hidden_exercises"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), primary_key=True)

