# Security & Persistence Report

## 1. Overview
The FastAPI backend lets users register, log in, create private conversations, and save
messages (both the user's and the assistant's) in a SQLite database via SQLAlchemy.
Each user can only ever see and modify their own data.

## 2. Database schema

```
users                      conversations                 messages
-----                      -------------                 --------
id            PK           id              PK            id               PK
email         UNIQUE       user_id         FK -> users   conversation_id  FK -> conversations
password_hash              title                         role  ("user" | "assistant")
created_at                 created_at                    content
                                                         created_at
```

- One **user** has many **conversations**; one **conversation** has many **messages**.
- `user_id` and `conversation_id` are indexed because every query filters on them.
- Deleting a user or conversation cascades to its children (no orphaned private data).
- `password_hash` holds a bcrypt hash (salted, slow by design). The raw password is
  never stored, logged, or returned.

## 3. Authentication flow

1. **Register** `POST /auth/register` — validates the email and password (min 8 chars),
   rejects duplicates (409), hashes the password with bcrypt, stores the user.
2. **Login** `POST /auth/login` — checks the password against the stored hash. On success
   it returns a signed JWT (`sub` = user id, `exp` = 30 minutes, HS256, key from the
   `SECRET_KEY` environment variable). Wrong email and wrong password give the same
   401 message, so attackers can't learn which emails exist.
3. **Authenticated requests** send `Authorization: Bearer <token>`. The
   `get_current_user` dependency verifies the signature and expiry, loads the user from
   the DB, and returns 401 if anything is wrong. Every conversation endpoint depends on it.

## 4. Ownership rule

> A conversation may only be accessed by the user whose `id` equals `conversation.user_id`.

Implemented once, in the `get_owned_conversation` dependency, which queries by
**both** `conversation_id` and `user_id = current_user.id`. All
per-conversation endpoints (read, add message) use it, so the rule can't be forgotten
on a single route. The list endpoint filters by `user_id` as well.

If the conversation belongs to someone else, the API returns **404, not 403**. This way
an attacker cannot tell the difference between "doesn't exist" and "not yours", and so
cannot enumerate valid IDs.

The `user_id` always comes from the verified token, never from the request body, so a
client cannot claim to be someone else.

## 5. Test proving private data is protected

`tests/test_privacy.py::test_user_b_cannot_read_or_modify_user_a_conversation`

1. User A and User B register and log in.
2. A creates a conversation and sends the message "my private note".
3. B tries `GET /conversations/{A's id}` -> **404**.
4. B tries `POST /conversations/{A's id}/messages` -> **404**.
5. B's `GET /conversations` -> `[]`.
6. A's conversation still contains exactly 2 messages (user + assistant), proving B's
   write attempt changed nothing.

Supporting tests: unauthenticated and garbage-token requests return 401; the database
contains a bcrypt hash rather than the plain password; wrong password returns 401.

Run with: `python -m pytest -q` (result: 4 passed).

## 6. Cache vs. database

`GET /ai/define?term=...` demonstrates a simple in-memory TTL cache (5 minutes) for a
repeated, **non-sensitive** AI result. In production the same idea is a Redis
`SETEX` / `GET`.

| | Cache (memory / Redis) | Database (SQLite) |
|---|---|---|
| Purpose | Speed, fewer repeated AI calls and cost | Source of truth |
| Lifetime | Temporary: TTL expiry, restart, or eviction can erase it | Permanent until deleted |
| Safe to lose? | Yes, it can be recomputed | No, it is the user's history |
| What goes in | Public/repeatable results (definitions) | Users, conversations, messages |

**Rule:** private conversation content is never cached by prompt, because a shared cache
key could return one user's answer to another. The cache key here contains only the
public term. Anything that must survive a restart goes in the database.

## 7. Known limitations / next steps
- Replace the default dev `SECRET_KEY` via environment variable before deploying.
- Add login rate limiting and refresh tokens.
- Use Alembic migrations instead of `create_all`, and PostgreSQL for multi-user scale.
- Serve over HTTPS only.
