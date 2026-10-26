"""CLI entry point: `python -m invoice_chaser.cli run --data sample_data/clients.json`"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

from .models import Invoice, InvoiceStatus
from .paypal_client import PayPalClient, PayPalNotConfigured
from .reminder_agent import draft_reminder


def load_invoices(path: str):
    with open(path, "r") as f:
        raw = json.load(f)
    return [Invoice.from_dict(d) for d in raw]


def save_invoices(path: str, invoices):
    with open(path, "w") as f:
        json.dump([inv.to_dict() for inv in invoices], f, indent=2)


def run(data_path: str, dry_run: bool = True) -> None:
    invoices = load_invoices(data_path)
    client = None if dry_run else PayPalClient()

    for inv in invoices:
        print(f"\n--- {inv.client_name} | {inv.description} | {inv.amount} {inv.currency} "
              f"| due {inv.due_date} | status {inv.status.value} ---")

        if inv.status == InvoiceStatus.DRAFT:
            if dry_run:
                print("[dry-run] would create + send PayPal invoice")
                inv.status = InvoiceStatus.SENT
            else:
                try:
                    inv.paypal_invoice_id = client.create_invoice(inv)
                    inv.status = InvoiceStatus.SENT
                    print(f"Created + sent PayPal invoice {inv.paypal_invoice_id}")
                except PayPalNotConfigured as e:
                    print(f"[skipped] {e}")
                    continue

        decision = draft_reminder(inv)
        if decision.should_send:
            print(f"Reminder tone: {decision.tone.value}")
            print(f"Subject: {decision.subject}")
            print(f"Note: {decision.note}")
            if dry_run:
                print("[dry-run] would send this reminder via PayPal")
            else:
                try:
                    client.send_reminder(inv.paypal_invoice_id, decision.subject, decision.note)
                    print("Reminder sent via PayPal.")
                except PayPalNotConfigured as e:
                    print(f"[skipped] {e}")
                    continue
            inv.reminders_sent += 1
            inv.last_reminder_sent_at = datetime.now()
        else:
            print("No reminder needed today.")

    save_invoices(data_path, invoices)


def main():
    parser = argparse.ArgumentParser(description="Invoice Chaser Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run one pass of the agent loop over all invoices")
    run_p.add_argument("--data", default="sample_data/clients.json")
    run_p.add_argument("--dry-run", action="store_true", default=False)

    args = parser.parse_args()
    if args.command == "run":
        run(args.data, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
