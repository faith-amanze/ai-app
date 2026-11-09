from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas
from .ai import generate_reply
from .cache import cache
from .database import Base, engine, get_db
from .deps import get_current_user, get_owned_conversation
from .security import create_access_token, hash_password, verify_password

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Private AI Chat API")


# ---------- Auth ----------
@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = models.User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Swagger's "Authorize" button sends the email in the `username` field.
    user = db.query(models.User).filter(models.User.email == form.username.lower()).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return schemas.Token(access_token=create_access_token(user.id))


# ---------- Conversations (all protected) ----------
@app.post("/conversations", response_model=schemas.ConversationOut, status_code=201)
def start_conversation(
    data: schemas.ConversationCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = models.Conversation(user_id=user.id, title=data.title)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@app.get("/conversations", response_model=list[schemas.ConversationOut])
def list_my_conversations(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user.id)
        .order_by(models.Conversation.id.desc())
        .all()
    )


@app.get("/conversations/{conversation_id}", response_model=schemas.ConversationDetail)
def get_conversation(convo: models.Conversation = Depends(get_owned_conversation)):
    return convo


@app.post(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.ExchangeOut,
    status_code=201,
)
def add_message(
    data: schemas.MessageCreate,
    convo: models.Conversation = Depends(get_owned_conversation),
    db: Session = Depends(get_db),
):
    user_msg = models.Message(conversation_id=convo.id, role="user", content=data.content)
    db.add(user_msg)
    db.commit()  # persist the user's message even if the AI call fails

    history = [{"role": m.role, "content": m.content} for m in convo.messages]
    try:
        reply = generate_reply(history)
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI provider failed; your message was saved")

    assistant_msg = models.Message(conversation_id=convo.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return {"user_message": user_msg, "assistant_message": assistant_msg}


# ---------- Optional cache demo ----------
@app.get("/ai/define")
def define(term: str, user: models.User = Depends(get_current_user)):
    """Non-sensitive, repeatable AI result -> safe to cache. The key is ONLY the term,
    so never put private conversation content through this path."""
    key = f"define:{term.strip().lower()}"
    cached = cache.get(key)
    if cached is not None:
        return {"term": term, "definition": cached, "cached": True}
    answer = generate_reply([{"role": "user", "content": f"Define '{term}' in one sentence."}])
    cache.set(key, answer)
    return {"term": term, "definition": answer, "cached": False}
