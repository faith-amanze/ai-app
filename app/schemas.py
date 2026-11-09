from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=200)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ExchangeOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
