from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserRead(BaseModel):
    email: EmailStr
    name: str
    # allow pydantic to access sqlalchemy object via dot like User.name
    model_config = {"from_attributes": True}
