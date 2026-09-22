from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import HTTPException, Request


def compute_hmac_sha256(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_stripe_signature(raw_body: bytes, stripe_signature: str, secret: str) -> bool:
    if not secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret is not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    try:
        import stripe

        stripe.Webhook.construct_event(raw_body, stripe_signature, secret)
        return True
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")


def verify_paypal_signature(raw_body: bytes, headers: dict[str, Any], secret: str) -> bool:
    if not secret:
        raise HTTPException(status_code=500, detail="PayPal webhook secret is not configured")
    transmission_id = headers.get("paypal-transmission-id")
    timestamp = headers.get("paypal-transmission-time")
    signature = headers.get("paypal-transmission-sig")
    if not all([transmission_id, timestamp, signature]):
        raise HTTPException(status_code=400, detail="Missing PayPal signature headers")

    signed_payload = f"{transmission_id}|{timestamp}|{signature}".encode("utf-8")
    expected = compute_hmac_sha256(secret, signed_payload)
    provided = hashlib.sha256(raw_body).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=400, detail="Invalid PayPal signature")
    return True


def verify_plaid_signature(raw_body: bytes, verification_header: str | None, secret: str) -> bool:
    if not secret:
        raise HTTPException(status_code=500, detail="Plaid webhook secret is not configured")
    if not verification_header:
        raise HTTPException(status_code=400, detail="Missing Plaid signature header")

    expected = compute_hmac_sha256(secret, raw_body)
    if not hmac.compare_digest(expected, verification_header):
        raise HTTPException(status_code=400, detail="Invalid Plaid signature")
    return True


def event_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    material = (
        f"{prev_hash}|"
        f"{payload.get('gateway', '')}|"
        f"{payload.get('event_id', '')}|"
        f"{payload.get('event_type', '')}|"
        f"{payload.get('entity_name', '')}|"
        f"{payload.get('amount', '')}|"
        f"{payload.get('currency', '')}|"
        f"{payload.get('timestamp', '')}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
