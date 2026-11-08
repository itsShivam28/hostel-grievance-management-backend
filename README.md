# Hostel Grievance Management System – Backend

FastAPI + PostgreSQL + SQLAlchemy 2 + Pydantic v2, with JWT auth and role-based access (STUDENT / WARDEN).
Requires Python 3.11+.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # set DATABASE_URL and a long random JWT_SECRET_KEY
uvicorn app.main:app --reload
```

Interactive docs: http://localhost:8000/docs (use **Authorize** with a student/warden email + password).

### Creating a warden

Public registration only ever creates **students**, so nobody can self-promote to warden.
Wardens are created from the command line (the password is prompted, never passed as an argument):

```bash
python -m app.cli create-warden --email warden@iiitdmj.ac.in --hostel "Aryabhatta Hostel"
```

## Project layout

```
app/
  main.py            app factory, lifespan (table creation + urgency scheduler)
  database.py        engine, session factory, Base, get_db
  cli.py             create-warden command
  core/              settings, JWT + password hashing, error types
  models/            User, Workman, Complaint (+ enums)
  schemas/           Pydantic request/response models
  crud/              database queries
  services/          business rules (auth, complaint workflow, urgency job)
  dependencies/      auth + RBAC dependencies, pagination
  routers/           auth, student, warden
tests/               pytest suite
```

## API

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/auth/register` | public | Register a student (`@iiitdmj.ac.in` only) |
| POST | `/auth/login` | public | OAuth2 password form (`username` = email) → JWT |
| GET | `/auth/me` | any | Current user |
| POST | `/student/complaints` | student | File a complaint (starts `PENDING`) |
| GET | `/student/complaints` | student | Own complaints; includes `point_of_contact` while `WORKING` |
| POST | `/student/complaints/{id}/verify` | student | Confirm work done → `RESOLVED`, `student_verified = true` |
| GET | `/warden/complaints?status=` | warden | Complaints for the warden's hostel (urgent first) |
| POST | `/warden/complaints/{id}/assign` | warden | Assign workman to a `PENDING` complaint → `WORKING` |
| POST | `/warden/complaints/{id}/close` | warden | Close; only allowed if `student_verified` |
| GET / POST | `/warden/workmen` | warden | List / register workmen |
| GET | `/health` | public | Liveness check |

List endpoints accept `offset` and `limit` (max 100).

## Business rules worth knowing

- **Lifecycle:** `PENDING → WORKING` (warden assigns) `→ RESOLVED` (student verifies) `→ CLOSED` (warden closes).
  Any out-of-order action returns `409`.
- **Scoping:** a student only reaches their own complaints and a warden only their own hostel's. Anything else is a `404`, so IDs of other users' complaints are not revealed.
- **Hostel names** are stored uppercased with whitespace collapsed, so `"Hostel  a"` and `"HOSTEL A"` match.
- **Urgency:** a background task started in the app lifespan runs at startup and then every
  `URGENCY_CHECK_INTERVAL_MINUTES` (default 60). It sets `is_urgent = true` on every complaint that is not
  `CLOSED` and older than `URGENT_AFTER_DAYS` (default 7). The update is a single idempotent statement, so
  running it from several workers is harmless. The core logic is `flag_overdue_complaints` in
  `app/services/urgency.py`, which can also be called from cron or a CLI.
- State changes lock the complaint row (`SELECT … FOR UPDATE`), so two wardens cannot assign the same complaint at once.

## Tests and checks

```bash
pip install -r requirements-dev.txt

pytest                         # runs against in-memory SQLite
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/test_db pytest   # runs against PostgreSQL
mypy                           # strict type-check (app + tests)
ruff check . && ruff format --check .
```

The PostgreSQL test database is created and dropped table-by-table on every test, so point it at a scratch database.

## Going to production

- Set `CREATE_TABLES_ON_STARTUP=false` and manage the schema with Alembic migrations.
- Use a strong, unique `JWT_SECRET_KEY` and serve behind HTTPS.
- Tokens are not revocable before they expire (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 60).
