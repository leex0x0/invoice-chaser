"""Data model for invoices the agent tracks."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


@dataclass
class Invoice:
    client_name: str
    client_email: str
    amount: float
    currency: str
    due_date: date
    description: str = ""
    status: InvoiceStatus = InvoiceStatus.DRAFT
    paypal_invoice_id: Optional[str] = None
    reminders_sent: int = 0
    last_reminder_sent_at: Optional[datetime] = None

    def days_overdue(self, today: Optional[date] = None) -> int:
        today = today or date.today()
        return (today - self.due_date).days

    def to_dict(self) -> dict:
        return {
            "client_name": self.client_name,
            "client_email": self.client_email,
            "amount": self.amount,
            "currency": self.currency,
            "due_date": self.due_date.isoformat(),
            "description": self.description,
            "status": self.status.value,
            "paypal_invoice_id": self.paypal_invoice_id,
            "reminders_sent": self.reminders_sent,
            "last_reminder_sent_at": (
                self.last_reminder_sent_at.isoformat() if self.last_reminder_sent_at else None
            ),
        }

    @staticmethod
    def from_dict(d: dict) -> "Invoice":
        return Invoice(
            client_name=d["client_name"],
            client_email=d["client_email"],
            amount=float(d["amount"]),
            currency=d.get("currency", "USD"),
            due_date=date.fromisoformat(d["due_date"]),
            description=d.get("description", ""),
            status=InvoiceStatus(d.get("status", "DRAFT")),
            paypal_invoice_id=d.get("paypal_invoice_id"),
            reminders_sent=d.get("reminders_sent", 0),
        )
