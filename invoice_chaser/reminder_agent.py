"""The decision-making core of the agent: when to nudge, and what to say.

This is deliberately deterministic/template-based so the whole demo runs
offline with zero API keys. `draft_with_llm` is a clearly marked hook where
a real LLM call can replace the templates for more natural copy without
touching the decision logic in `should_send_reminder` / `choose_tone`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from .models import Invoice


class Tone(str, Enum):
    HEADS_UP = "heads_up"          # not due yet
    LIGHT = "light"                # 0-3 days overdue
    DIRECT = "direct"              # 4-10 days overdue
    FIRM = "firm"                  # 11-20 days overdue
    ESCALATION = "escalation"      # 21+ days overdue


@dataclass
class ReminderDecision:
    should_send: bool
    tone: Optional[Tone]
    subject: str = ""
    note: str = ""


MIN_DAYS_BETWEEN_REMINDERS = 3


def choose_tone(days_overdue: int) -> Tone:
    if days_overdue < 0:
        return Tone.HEADS_UP
    if days_overdue <= 3:
        return Tone.LIGHT
    if days_overdue <= 10:
        return Tone.DIRECT
    if days_overdue <= 20:
        return Tone.FIRM
    return Tone.ESCALATION


def should_send_reminder(invoice: Invoice, today: Optional[date] = None) -> bool:
    today = today or date.today()
    if invoice.status.value == "PAID" or invoice.status.value == "CANCELLED":
        return False
    days_overdue = invoice.days_overdue(today)
    # Heads-up reminder only once, a few days before due date.
    if days_overdue < -3:
        return False
    if invoice.last_reminder_sent_at is not None:
        gap = (today - invoice.last_reminder_sent_at.date()).days
        if gap < MIN_DAYS_BETWEEN_REMINDERS:
            return False
    return True


TEMPLATES = {
    Tone.HEADS_UP: (
        "Quick heads-up: invoice for {description}",
        "Hi {client_name}, just a friendly heads-up that the invoice for "
        "{description} ({amount} {currency}) is due on {due_date}. No action "
        "needed if it's already scheduled — just flagging it early.",
    ),
    Tone.LIGHT: (
        "Friendly reminder: invoice due",
        "Hi {client_name}, hope you're doing well! Just noticed the invoice "
        "for {description} ({amount} {currency}) was due on {due_date}. "
        "Totally understand if it slipped through — here's the link whenever "
        "you get a chance.",
    ),
    Tone.DIRECT: (
        "Reminder: invoice now {days_overdue} days overdue",
        "Hi {client_name}, following up on the invoice for {description} "
        "({amount} {currency}), which was due {due_date} and is now "
        "{days_overdue} days overdue. Could you let me know when payment "
        "is scheduled?",
    ),
    Tone.FIRM: (
        "Action needed: invoice {days_overdue} days overdue",
        "Hi {client_name}, this invoice for {description} ({amount} "
        "{currency}) is now {days_overdue} days past its {due_date} due "
        "date. Please arrange payment as soon as possible, or reach out if "
        "there's an issue I should know about.",
    ),
    Tone.ESCALATION: (
        "Overdue invoice — let's resolve this",
        "Hi {client_name}, this invoice for {description} ({amount} "
        "{currency}) is now {days_overdue} days overdue (due {due_date}). "
        "I'd like to get this resolved — happy to hop on a quick call if "
        "something's blocking payment, otherwise please process it at your "
        "earliest convenience.",
    ),
}


def draft_reminder(invoice: Invoice, today: Optional[date] = None) -> ReminderDecision:
    today = today or date.today()
    if not should_send_reminder(invoice, today):
        return ReminderDecision(should_send=False, tone=None)

    days_overdue = invoice.days_overdue(today)
    tone = choose_tone(days_overdue)
    subject_tpl, note_tpl = TEMPLATES[tone]

    ctx = {
        "client_name": invoice.client_name,
        "description": invoice.description or "services",
        "amount": f"{invoice.amount:.2f}",
        "currency": invoice.currency,
        "due_date": invoice.due_date.isoformat(),
        "days_overdue": days_overdue,
    }
    subject = subject_tpl.format(**ctx)
    note = note_tpl.format(**ctx)

    # Hook for a real LLM: swap the template note for a generated one, e.g.
    #   note = draft_with_llm(invoice, tone, ctx)
    # while keeping should_send/choose_tone as the deterministic decision core.

    return ReminderDecision(should_send=True, tone=tone, subject=subject, note=note)


def draft_with_llm(invoice: Invoice, tone: Tone, ctx: dict) -> str:  # pragma: no cover
    """Placeholder hook: plug in an LLM call here for more natural copy.

    Left unimplemented on purpose — the demo works fully offline without it.
    """
    raise NotImplementedError("Plug an LLM call in here if you want generated copy.")
