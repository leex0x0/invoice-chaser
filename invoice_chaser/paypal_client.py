"""Thin wrapper over the PayPal Invoicing REST API.

Works against the sandbox base URL by default. Needs PAYPAL_CLIENT_ID /
PAYPAL_CLIENT_SECRET in the environment (see .env.example). If they are
missing, every method raises PayPalNotConfigured so callers can fall back
to --dry-run instead of crashing.
"""
from __future__ import annotations

import os
import time
from typing import Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

from .models import Invoice

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
LIVE_BASE = "https://api-m.paypal.com"


class PayPalNotConfigured(RuntimeError):
    pass


class PayPalClient:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None,
                 live: bool = False):
        self.client_id = client_id or os.environ.get("PAYPAL_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("PAYPAL_CLIENT_SECRET")
        self.base_url = LIVE_BASE if live else SANDBOX_BASE
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _ensure_configured(self):
        if requests is None:
            raise PayPalNotConfigured(
                "The 'requests' package is not installed. Run with --dry-run, "
                "or `pip install requests` to make real sandbox calls."
            )
        if not self.client_id or not self.client_secret:
            raise PayPalNotConfigured(
                "PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET not set. "
                "Create a free sandbox app at developer.paypal.com and put the "
                "credentials in .env, or run with --dry-run."
            )

    def _get_access_token(self) -> str:
        self._ensure_configured()
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        resp = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    def create_invoice(self, invoice: Invoice) -> str:
        """Create + send a draft invoice. Returns the PayPal invoice id."""
        payload = {
            "detail": {
                "currency_code": invoice.currency,
                "note": invoice.description or "Thanks for the business!",
                "terms_and_conditions": "Payment due on receipt unless otherwise agreed.",
            },
            "invoicer": {},
            "primary_recipients": [
                {"billing_info": {"email_address": invoice.client_email}}
            ],
            "items": [
                {
                    "name": invoice.description or "Services rendered",
                    "quantity": "1",
                    "unit_amount": {"currency_code": invoice.currency, "value": f"{invoice.amount:.2f}"},
                }
            ],
            "due_date": invoice.due_date.isoformat(),
        }
        resp = requests.post(
            f"{self.base_url}/v2/invoicing/invoices",
            headers=self._headers(),
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        invoice_id = resp.json().get("id") or resp.headers.get("Location", "").rstrip("/").split("/")[-1]

        send_resp = requests.post(
            f"{self.base_url}/v2/invoicing/invoices/{invoice_id}/send",
            headers=self._headers(),
            json={"send_to_invoicer": False},
            timeout=20,
        )
        send_resp.raise_for_status()
        return invoice_id

    def send_reminder(self, paypal_invoice_id: str, subject: str, note: str) -> None:
        resp = requests.post(
            f"{self.base_url}/v2/invoicing/invoices/{paypal_invoice_id}/remind",
            headers=self._headers(),
            json={"subject": subject, "note": note, "send_to_recipient": True},
            timeout=20,
        )
        resp.raise_for_status()

    def get_invoice_status(self, paypal_invoice_id: str) -> str:
        resp = requests.get(
            f"{self.base_url}/v2/invoicing/invoices/{paypal_invoice_id}",
            headers=self._headers(),
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("status", "UNKNOWN")
