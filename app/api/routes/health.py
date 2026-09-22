from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.models import PaymentWebhookEvent
from app.queue import AUDIT_QUEUE, enqueue_audit_record
from app.schemas import PaymentWebhookPayload
from app.security import verify_paypal_signature, verify_plaid_signature, verify_stripe_signature

router = APIRouter(prefix="/api/v2", tags=["webhooks"])


@router.post("/webhooks/payments")
async def ingest_payment_webhook(
    request: Request,
    payload: PaymentWebhookPayload,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    paypal_transmission_id: str | None = Header(default=None, alias="Paypal-Transmission-Id"),
    paypal_transmission_time: str | None = Header(default=None, alias="Paypal-Transmission-Time"),
    paypal_transmission_sig: str | None = Header(default=None, alias="Paypal-Transmission-Sig"),
    plaid_verification: str | None = Header(default=None, alias="Plaid-Webhook-Verification"),
):
    raw_body = await request.body()

    if payload.gateway == "stripe":
        verify_stripe_signature(raw_body, stripe_signature, settings.stripe_webhook_secret)
    elif payload.gateway == "paypal":
        verify_paypal_signature(
            raw_body,
            {
                "paypal-transmission-id": paypal_transmission_id,
                "paypal-transmission-time": paypal_transmission_time,
                "paypal-transmission-sig": paypal_transmission_sig,
            },
            settings.paypal_webhook_secret,
        )
    elif payload.gateway == "plaid":
        verify_plaid_signature(raw_body, plaid_verification, settings.plaid_webhook_secret)

    async with SessionLocal() as session:
        existing = await session.execute(
            select(PaymentWebhookEvent).where(
                PaymentWebhookEvent.gateway == payload.gateway,
                PaymentWebhookEvent.event_id == payload.event_id,
            )
        )
        if existing.scalar_one_or_none():
            return {
                "status": "duplicate",
                "gateway": payload.gateway,
                "event_id": payload.event_id,
                "message": "Event already processed; idempotent replay ignored.",
                "audit_committed": False,
            }

        event = PaymentWebhookEvent(
            gateway=payload.gateway,
            event_id=payload.event_id,
            event_type=payload.event_type,
            entity_name=payload.entity_name,
            amount=float(payload.amount),
            currency=payload.currency,
            customer_ref=payload.customer_ref,
            status="received",
            signature_valid=True,
            raw_payload=payload.model_dump(mode="json"),
        )
        session.add(event)
        await session.flush()

        audit_payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "admin_node": "Gtom198244@gmail.com",
            "module": "Payment Load & Webhook Gateway",
            "gateway": payload.gateway,
            "event_id": payload.event_id,
            "event_type": payload.event_type,
            "entity_name": payload.entity_name,
            "amount": float(payload.amount),
            "currency": payload.currency,
            "status": "processed_and_queued",
            "ledger_verified": True,
            "event_db_id": event.id,
        }

        try:
            await enqueue_audit_record(audit_payload)
            event.status = "queued"
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=500, detail="Unable to enqueue audit record")

    return {
        "status": "success",
        "gateway": payload.gateway,
        "event_id": payload.event_id,
        "message": f"Successfully ingested and queued {payload.event_type} for {payload.entity_name}.",
        "audit_committed": True,
    }
