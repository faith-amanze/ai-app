# Private AI Chat API (FastAPI + SQLAlchemy + JWT)

```bash
pip install -r requirements.txt
export SECRET_KEY=$(openssl rand -hex 32)
# optional: export ANTHROPIC_API_KEY=...   (otherwise a stub assistant replies)
uvicorn app.main:app --reload     # docs at http://127.0.0.1:8000/docs
python -m pytest -q
```

Endpoints: `POST /auth/register`, `POST /auth/login`, `POST /conversations`,
`GET /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/messages`,
`GET /ai/define?term=` (cached demo).

See `docs/security-persistence-report.md`.
