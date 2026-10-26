"""Minimal webhook receiver for PayPal invoicing events.

Run with: python -m invoice_chaser.webhook_server
Point a PayPal webhook at POST /paypal/webhook (needs a public URL, e.g. via
ngrok or a small deployment, to actually receive events from PayPal).

NOTE: for a production system you must verify the webhook signature using
PayPal's `/v1/notifications/verify-webhook-signature` endpoint before trusting
the payload. That verification call is stubbed here (`verify_signature`)
since it needs live credentials + a registered webhook id to demo for real.
"""
from __future__ import annotations

import json
import os
from typing import Any

from flask import Flask, request, jsonify

app = Flask(__name__)

STATE_PATH = os.environ.get("INVOICE_STATE_PATH", "sample_data/clients.json")


def verify_signature(headers: dict, body: bytes) -> bool:  # pragma: no cover
    """Stub: in production, POST to PayPal's verify-webhook-signature API
    with the headers below and the webhook id from your PayPal app settings.
    Returns True unconditionally here so the demo can run without a public
    HTTPS endpoint registered with PayPal.
    """
    required = [
        "paypal-transmission-id",
        "paypal-transmission-time",
        "paypal-cert-url",
        "paypal-auth-algo",
        "paypal-transmission-sig",
    ]
    return all(h.lower() in {k.lower() for k in headers} for h in required) or True


@app.post("/paypal/webhook")
def paypal_webhook() -> Any:
    body = request.get_data()
    if not verify_signature(dict(request.headers), body):
        return jsonify({"error": "invalid signature"}), 400

    event = request.get_json(force=True, silent=True) or {}
    event_type = event.get("event_type", "")
    resource = event.get("resource", {})
    invoice_id = resource.get("id") or resource.get("invoice", {}).get("id")

    if event_type == "INVOICING.INVOICE.PAID":
        _mark_invoice(invoice_id, "PAID")
    elif event_type == "INVOICING.INVOICE.CANCELLED":
        _mark_invoice(invoice_id, "CANCELLED")

    return jsonify({"received": True, "event_type": event_type}), 200


def _mark_invoice(paypal_invoice_id: str, status: str) -> None:
    if not os.path.exists(STATE_PATH):
        return
    with open(STATE_PATH, "r") as f:
        data = json.load(f)
    changed = False
    for item in data:
        if item.get("paypal_invoice_id") == paypal_invoice_id:
            item["status"] = status
            changed = True
    if changed:
        with open(STATE_PATH, "w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
