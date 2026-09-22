from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PaymentWebhookPayload(BaseModel):
    gateway: str = Field(..., description='One of: stripe, paypal, plaid')
    event_id: str
    event_type: str
    entity_name: str
    amount: Decimal
    currency: str = "USD"
    customer_ref: str | None = None

    @field_validator("gateway")
    @classmethod
    def validate_gateway(cls, value: str) -> str:
        allowed = {"stripe", "paypal", "plaid"}
        normalized = value.lower().strip()
        if normalized not in allowed:
            raise ValueError("gateway must be one of: stripe, paypal, plaid")
        return normalized

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("amount must be greater than 0")
        return value
