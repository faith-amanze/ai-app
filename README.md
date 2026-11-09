# Private AI Chat API

A FastAPI backend where users register, log in, and keep private conversations
saved in a SQLite database. Each user can only read and modify their own data.

## Features
- SQLAlchemy + SQLite with `users`, `conversations`, and `messages` tables
- Registration with bcrypt password hashing (raw passwords are never stored)
- Login that returns a JWT access token
- Protected conversation endpoints with an ownership check (other users get 404)
- Saves both the user message and the assistant reply
- Optional in-memory cache demo (`GET /ai/define`)

## Setup (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = "use-a-long-random-string"
python -m uvicorn app.main:app --reload
```

## Setup (Mac / Linux)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="use-a-long-random-string"
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive Swagger UI.
Set `ANTHROPIC_API_KEY` to get real AI replies; without it a stub assistant replies.

## Endpoints
| Method | Path | Auth |
|---|---|---|
| POST | /auth/register | no |
| POST | /auth/login | no |
| POST | /conversations | yes |
| GET | /conversations | yes |
| GET | /conversations/{id} | yes (owner only) |
| POST | /conversations/{id}/messages | yes (owner only) |
| GET | /ai/define?term= | yes |

## Tests
`tests/test_privacy.py` proves that User B cannot read or write User A's conversation.

## Report
See [docs/security-persistence-report.md](docs/security-persistence-report.md) for the
schema, auth flow, ownership rule, and the privacy test.
