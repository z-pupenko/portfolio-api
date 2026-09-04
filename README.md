# Portfolio API

[![CI](https://github.com/z-pupenko/portfolio-api/actions/workflows/ci.yml/badge.svg)](https://github.com/z-pupenko/portfolio-api/actions/workflows/ci.yml)

A REST-style portfolio management API built with FastAPI, SQLAlchemy, and
PostgreSQL. It tracks portfolios, assets, prices, and buy/sell transactions,
then calculates cash balances, holdings, and portfolio valuations.

The project also supports atomic CSV transaction imports. Pandas normalizes
and summarizes uploaded data, Pydantic validates each row, and SQLAlchemy saves
the full batch in one database transaction.

Users register with email and password, authenticate through an OAuth2 password
flow, and receive short-lived signed JWT access tokens. Portfolio and transaction
operations are scoped to the authenticated owner.

## Features

- Create, retrieve, update, and delete portfolios
- Create and list assets
- Record asset prices and retrieve the latest price
- Create, retrieve, update, delete, and list transactions
- Reject purchases with insufficient cash
- Reject sales that exceed the quantity currently held
- Serialize transaction writes per portfolio with PostgreSQL row-level locks
- Reject transaction deletions that would leave negative cash or holdings
- Calculate portfolio cash balance and holdings
- Calculate portfolio value from the latest asset prices
- Summarize transaction activity by asset and currency over an optional date range
- Import transactions from CSV with row-level validation errors
- Roll back the entire CSV batch when any transaction fails
- Return per-asset CSV import summaries using Pandas
- Manage database schema changes with Alembic
- Validate application configuration at startup
- Register users with Argon2 password hashing
- Authenticate with OAuth2 bearer tokens and signed JWTs
- Restrict portfolios, transactions, imports, and calculations to their owner
- Expose separate liveness and database-readiness health checks
- Emit structured JSON request logs with request IDs and response timings
- Reject unsafe production settings without exposing secret input values

## Technology

- Python 3.14
- FastAPI
- Pydantic and pydantic-settings
- SQLAlchemy 2
- PostgreSQL with psycopg
- Alembic
- Pandas
- Pytest
- Ruff

## Project structure

```text
app/
├── routers/                 # HTTP endpoints and HTTP error translation
│   ├── assets.py
│   ├── auth.py
│   ├── health.py
│   ├── portfolios.py
│   ├── transactions.py
│   └── lookups.py
├── services/                # Business rules and calculations
│   ├── portfolios.py
│   ├── transactions.py
│   ├── transaction_imports.py
│   ├── analytics.py
│   └── users.py
├── config.py                # Environment-backed application settings
├── database.py              # SQLAlchemy engine and session dependency
├── dependencies.py          # Current-user authentication dependency
├── logging_config.py        # Structured JSON logging configuration
├── main.py                  # FastAPI application and router registration
├── middleware.py            # Request IDs, timings, and request logging
├── models.py                # SQLAlchemy database models
├── security.py              # Password hashing and JWT helpers
└── schemas.py               # Pydantic request and response schemas

alembic/                     # Database migrations
tests/                       # Unit, integration, and API tests
```

## Local setup

### Docker Compose (recommended)

Install Docker Desktop, then copy the environment template:

```powershell
Copy-Item .env.example .env
```

Replace the example database password and JWT secret in `.env`, then build and
start the API and PostgreSQL:

```powershell
docker compose up --build
```

The API waits for PostgreSQL to become healthy, applies Alembic migrations, and
then starts Uvicorn. Open Swagger UI at <http://127.0.0.1:8000/docs>.

Stop the containers with:

```powershell
docker compose down
```

PostgreSQL data remains in a named Docker volume between container restarts.
To deliberately remove that data as well, use `docker compose down --volumes`.

### Manual setup

#### 1. Create and activate a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 2. Install development dependencies

```powershell
python -m pip install -r requirements-dev.txt
```

#### 3. Configure PostgreSQL

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Update `.env` with credentials for an existing PostgreSQL database:

```dotenv
APP_NAME=Portfolio API
APP_ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

DB_USER=portfolio_user
DB_PASSWORD=change-me
DB_HOST=localhost
DB_PORT=5432
DB_NAME=portfolio_db

JWT_SECRET_KEY=replace-with-a-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

The application validates these settings during startup. The real `.env` file
is excluded from Git.

#### 4. Apply database migrations

```powershell
python -m alembic upgrade head
```

Run migrations against a live PostgreSQL database. The migration history
contains a data-dependent ownership backfill, so offline `--sql` generation is
intentionally unsupported.

#### 5. Start the API

```powershell
python -m uvicorn app.main:app --reload --no-access-log
```

Open the interactive API documentation at:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

### Health checks

- `GET /health/live` — confirms that the FastAPI process is running and responding.
- `GET /health/ready` — confirms that the API can connect to and query PostgreSQL. It returns `503 Service Unavailable` when the database cannot be reached.

Both endpoints are public so Docker and monitoring systems can call them without
an authentication token.

### Request logging

Successful and handled-error HTTP responses include an `X-Request-ID` header.
The application writes a structured JSON log containing that request ID, the
HTTP method, URL path, response status, and request duration. Successful
responses use the `INFO` log level, client errors use `WARNING`, and server
errors use `ERROR`.

Successful health probes use `DEBUG` to avoid filling normal logs with routine
container checks. Failed health probes keep their normal warning or error level.
Uvicorn's duplicate access log is disabled in the documented and containerized
startup commands because the middleware already records requests.

Set `LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` to control
which application logs are emitted. Request bodies, query parameters,
authorization headers, passwords, and access tokens are deliberately excluded.
Container platforms can collect the JSON records from the application's standard
output stream.

### Production configuration

Set `APP_ENVIRONMENT=production` only in a production environment. Production
startup rejects `DEBUG=true` and requires a JWT secret containing at least 32
characters. These checks run while the settings object is created, before the
FastAPI application begins accepting requests. Validation errors hide raw input
values so startup logs do not reveal database or JWT secrets.

Generate the real JWT secret outside the repository and provide it through the
deployment environment or a secret manager. `SecretStr` prevents accidental
display of the configured value, but it does not encrypt the value or make a
weak secret secure.

The container listens on `0.0.0.0:8000`; a future deployment platform must route
traffic to that internal port. Database credentials and the JWT secret must be
provided at runtime and must never be built into the Docker image.

## Authentication

Register a user with `POST /auth/register`, then request an access token from
`POST /auth/token`. The token endpoint uses form fields named `username` and
`password`; submit the user's email in the `username` field.

Send the returned token with protected requests:

```http
Authorization: Bearer <access-token>
```

Portfolio routes return only the authenticated user's portfolios. Requests for
another user's portfolio or transaction return `404` so private resource IDs
are not disclosed. Assets and asset prices remain a shared catalogue for all
authenticated users.

## Transaction summary

Retrieve an authenticated portfolio's transaction activity with:

```text
GET /portfolios/{portfolio_id}/transaction-summary
```

Optional `start_date` and `end_date` query parameters use ISO dates and are
inclusive. PostgreSQL filters and joins the relevant rows before Pandas builds
two report breakdowns: per asset and per currency. Currency totals remain
separate so values denominated in GBP, USD, or another currency are never added
together without foreign-exchange conversion.

Example:

```text
GET /portfolios/1/transaction-summary?start_date=2026-01-01&end_date=2026-06-30
```

## CSV transaction import

Send a `multipart/form-data` request containing a `.csv` file to:

```text
POST /portfolios/{portfolio_id}/transactions/import/
```

Required columns:

```text
asset_id,transaction_type,quantity,price,transaction_date
```

Optional columns:

```text
fees
```

Example:

```csv
asset_id,transaction_type,quantity,price,fees,transaction_date
1,buy,10,150.25,1.50,2026-08-01
2,buy,5,400.00,0,2026-08-02
1,sell,3,160.00,1.00,2026-08-05
```

Imports are limited to 5 MiB. Every row is validated before persistence, and
the database batch is atomic: either all transactions are saved or none are.

## Quality checks

Run the test suite:

```powershell
python -m pytest
```

Run lint checks:

```powershell
python -m ruff check app tests alembic
```

Check formatting:

```powershell
python -m ruff format --check app tests alembic
```

The current suite contains unit, integration, and API tests covering business
calculations, Pydantic schemas, configuration, persistence, and CSV imports.
CI also starts a disposable PostgreSQL service, applies the complete Alembic
migration history, checks for model/schema drift, and verifies database
constraints independently of Pydantic. PostgreSQL integration coverage also
forces concurrent sell attempts to overlap and verifies that portfolio row
locking prevents both requests from spending the same holdings.

## Current limitations

- Valuation currently requires asset currency to match portfolio base currency;
  foreign-exchange conversion is not implemented.
- Transaction summaries report monetary totals in each asset's native currency;
  they do not convert those totals into the portfolio base currency.
- Large imports run synchronously and are intentionally limited to 5 MiB.
- Access tokens are short-lived but do not yet support refresh tokens or a
  server-side revocation list.

These are planned areas for future development rather than hidden production
claims.
