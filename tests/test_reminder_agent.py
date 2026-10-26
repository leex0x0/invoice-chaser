import sys
import os
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from invoice_chaser.models import Invoice, InvoiceStatus
from invoice_chaser.reminder_agent import choose_tone, should_send_reminder, draft_reminder, Tone


def make_invoice(due_offset_days: int, status=InvoiceStatus.SENT, last_reminder_days_ago=None):
    today = date.today()
    inv = Invoice(
        client_name="Test Client",
        client_email="test@example.com",
        amount=100.0,
        currency="USD",
        due_date=today + timedelta(days=due_offset_days),
        description="Test work",
        status=status,
    )
    if last_reminder_days_ago is not None:
        inv.last_reminder_sent_at = datetime.now() - timedelta(days=last_reminder_days_ago)
    return inv


def test_choose_tone_boundaries():
    assert choose_tone(-5) == Tone.HEADS_UP
    assert choose_tone(0) == Tone.LIGHT
    assert choose_tone(3) == Tone.LIGHT
    assert choose_tone(4) == Tone.DIRECT
    assert choose_tone(10) == Tone.DIRECT
    assert choose_tone(11) == Tone.FIRM
    assert choose_tone(20) == Tone.FIRM
    assert choose_tone(21) == Tone.ESCALATION
    assert choose_tone(90) == Tone.ESCALATION


def test_no_reminder_when_paid():
    inv = make_invoice(due_offset_days=-5, status=InvoiceStatus.PAID)
    assert should_send_reminder(inv) is False


def test_no_reminder_too_soon_after_last_one():
    inv = make_invoice(due_offset_days=-5, last_reminder_days_ago=1)
    assert should_send_reminder(inv) is False


def test_reminder_allowed_after_gap():
    inv = make_invoice(due_offset_days=-5, last_reminder_days_ago=5)
    assert should_send_reminder(inv) is True


def test_draft_reminder_escalation_copy_mentions_days_overdue():
    inv = make_invoice(due_offset_days=-25)
    decision = draft_reminder(inv)
    assert decision.should_send is True
    assert decision.tone == Tone.ESCALATION
    assert "25 days overdue" in decision.note


def test_draft_reminder_not_due_yet_future():
    inv = make_invoice(due_offset_days=10)
    decision = draft_reminder(inv)
    assert decision.should_send is False
