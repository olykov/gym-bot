from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MuscleBase(BaseModel):
    name: str

class MuscleCreate(MuscleBase):
    pass

class Muscle(MuscleBase):
    id: int

    class Config:
        from_attributes = True

class ExerciseBase(BaseModel):
    name: str
    muscle: int

class ExerciseCreate(ExerciseBase):
    pass

class Exercise(ExerciseBase):
    id: int
    muscle_group: Optional[Muscle] = None

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    id: int
    first_name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None

class User(UserBase):
    class Config:
        from_attributes = True

class TrainingBase(BaseModel):
    date: datetime
    user_id: int
    muscle_id: int
    exercise_id: int
    set: int
    weight: float
    reps: float

class Training(TrainingBase):
    id: str
    muscle_group: Optional[Muscle] = None
    exercise: Optional[Exercise] = None
    user: Optional[User] = None

    class Config:
        from_attributes = True
