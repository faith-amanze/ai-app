import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models
from .database import get_db
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        user_id = decode_access_token(token)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get(models.User, user_id)
    if user is None:
        raise unauthorized
    return user


def get_owned_conversation(
    conversation_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.Conversation:
    """OWNERSHIP RULE: the query filters by BOTH id and user_id.
    Someone else's conversation is indistinguishable from a missing one (404, not 403),
    so attackers can't even discover which conversation IDs exist."""
    convo = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id, models.Conversation.user_id == user.id)
        .first()
    )
    if convo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return convo
