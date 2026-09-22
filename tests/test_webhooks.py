from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_webhook_ingest_success() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v2/webhooks/payments",
            json={
                "gateway": "stripe",
                "event_id": "evt_test_1",
                "event_type": "payment_intent.succeeded",
                "entity_name": "HELIOS EMPIRE LLC",
                "amount": 125.50,
                "currency": "USD",
                "customer_ref": "cust_123",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["gateway"] == "stripe"
        assert payload["event_id"] == "evt_test_1"


def test_webhook_ingest_duplicate_is_idempotent() -> None:
    with TestClient(app) as client:
        payload = {
            "gateway": "paypal",
            "event_id": "evt_test_2",
            "event_type": "checkout.completed",
            "entity_name": "FLORES EMPIRE LLC",
            "amount": 200.00,
            "currency": "USD",
            "customer_ref": "cust_456",
        }
        first = client.post("/api/v2/webhooks/payments", json=payload)
        second = client.post("/api/v2/webhooks/payments", json=payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["status"] == "duplicate"
