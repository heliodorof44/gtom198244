from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal
from app.models import PaymentAuditEntry, PaymentWebhookEvent
from app.security import event_hash

AUDIT_QUEUE: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=settings.audit_queue_size)


async def enqueue_audit_record(payload: dict[str, Any]) -> None:
    await AUDIT_QUEUE.put(payload)


async def persist_audit_event(session: AsyncSession, payload: dict[str, Any], event_db_id: int) -> None:
    last_record = await session.execute(
        select(PaymentAuditEntry).order_by(PaymentAuditEntry.id.desc()).limit(1)
    )
    last_audit = last_record.scalar_one_or_none()
    previous_hash = last_audit.hash if last_audit else "genesis"
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    chain_hash = event_hash(previous_hash, payload)

    entry = PaymentAuditEntry(
        event_id=event_db_id,
        gateway=payload["gateway"],
        event_type=payload["event_type"],
        entity_name=payload["entity_name"],
        amount=float(payload["amount"]),
        currency=payload["currency"],
        status="queued",
        prev_hash=previous_hash,
        hash=chain_hash,
        payload_hash=payload_hash,
    )
    session.add(entry)
    await session.commit()


async def process_audit_queue() -> None:
    while True:
        payload = await AUDIT_QUEUE.get()
        try:
            async with SessionLocal() as session:
                await persist_audit_event(session, payload, int(payload["event_db_id"]))
        except Exception as exc:  # pragma: no cover - actual process should log
            raise HTTPException(status_code=500, detail=f"Audit queue processing failed: {exc}") from exc
        finally:
            AUDIT_QUEUE.task_done()
