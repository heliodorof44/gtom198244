# FastAPI Multi-Gateway Payment Platform

This project provides a production-ready FastAPI foundation for ingesting, validating, and processing payment webhooks from Stripe, PayPal, and Plaid with a secure audit chain and asynchronous background processing.

## Features

- Multi-gateway webhook ingestion
- Signature validation hooks for Stripe, PayPal, and Plaid
- Idempotent event storage using gateway + event_id uniqueness
- Async audit queue with hash-chained ledger records
- SQLAlchemy persistence with SQLite for local/dev and PostgreSQL for production
- Docker and docker-compose setup
- Health checks and tests

## Quick start

1. Copy `.env.example` to `.env` and configure your secrets.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Test the payment webhook endpoint:

```bash
curl -X POST "http://localhost:8000/api/v2/webhooks/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "gateway": "stripe",
    "event_id": "evt_123",
    "event_type": "payment_intent.succeeded",
    "entity_name": "HELIOS EMPIRE LLC",
    "amount": 1250.50,
    "currency": "USD",
    "customer_ref": "cust_abc123"
  }'
```

## Production hardening notes

- Use environment-scoped secrets, never commit `.env`.
- Set `DATABASE_URL` to your managed PostgreSQL instance in production.
- Configure gateway-specific webhook secrets.
- Run the app behind a reverse proxy and TLS termination (nginx, Traefik, or a cloud LB).
- Add a durable queue or task broker (Celery, Redis/RQ, or Cloud Tasks) for mission-critical workloads if you need cross-process resilience.
- Keep full audit trail records in a separate append-only table or storage system for compliance use.

## Uvicorn scaling

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Docker

```bash
docker compose up --build
```

## License

Apache 2.0
