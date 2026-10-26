# Invoice Chaser Agent

An autonomous AI agent that chases unpaid invoices for small freelancers/agencies: it watches a list of invoices, drafts progressively firmer (but still polite) follow-up messages as they age, creates/send real PayPal invoices through the PayPal Invoicing REST API, and listens for PayPal webhooks to know the moment an invoice is paid so it can stop chasing automatically.

Built for the **PayPal AI Hackathon 2026** (Agentic Commerce & Autonomous Payments track).

## Why this is "agentic commerce"

This isn't a chatbot that *suggests* you follow up on an invoice. It actually:

1. Creates the PayPal invoice via the PayPal Invoicing API (sandbox).
2. Sends it to the client.
3. On a schedule, decides on its own whether a reminder is due, writes the reminder copy itself (tone escalates the longer it's overdue), and sends it.
4. Listens for `INVOICING.INVOICE.PAID` webhooks and marks the invoice as settled, stopping the chase loop without a human telling it to.

A human only sets up the client list once; the agent runs the rest of the loop.

## How it works

```
invoice_chaser/
  models.py        # Invoice + reminder data model
  paypal_client.py # Thin wrapper over PayPal Invoicing REST API (sandbox or live)
  reminder_agent.py# Decides *when* to nudge and *what tone* to use, drafts the message
  webhook_server.py# Minimal Flask app that receives PayPal webhooks and updates state
  cli.py           # `python -m invoice_chaser.cli run` entry point
tests/
  test_reminder_agent.py
sample_data/
  clients.json     # Example invoice list to run the demo against
```

### Reminder escalation logic (the "agent" part)

| Days overdue | Tone                          |
|---------------|-------------------------------|
| not yet due   | friendly heads-up, no pressure |
| 0-3 days      | light, assumes it slipped their mind |
| 4-10 days     | direct, restates amount + due date |
| 11-20 days    | firm, mentions late fee policy if any |
| 21+ days      | escalation notice, offers a call to resolve |

The agent picks the tone itself from how overdue the invoice is and from how many reminders have already gone out, so it never sends two identical nudges in a row.

## Running the demo (sandbox mode, no real money moves)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET from a PayPal Developer sandbox app
python -m invoice_chaser.cli run --data sample_data/clients.json --dry-run
```

`--dry-run` prints what the agent *would* create/send without calling PayPal, so you can see the whole decision loop with zero setup. Drop `--dry-run` once sandbox credentials are in `.env` to actually create sandbox invoices.

### Getting sandbox credentials (free, no real money)
1. Create a free PayPal Developer account at developer.paypal.com (business or personal, sandbox only).
2. Create a sandbox "app" to get a Client ID + Secret.
3. Put them in `.env`.

This step needs a real PayPal account, so it's left for a human to do; the agent code is ready to use the credentials the moment they exist.

## PayPal tech used
- PayPal Invoicing REST API (create/send invoice)
- PayPal Webhooks (`INVOICING.INVOICE.PAID`, `INVOICING.INVOICE.CANCELLED`)
- OAuth2 client-credentials flow for API auth

## AI used
- The reminder-tone/escalation decision logic and message drafting is the "AI agent" piece — it's implemented as deterministic+template logic here so the demo runs offline with zero API keys, but `reminder_agent.py` has a clearly marked `draft_with_llm()` hook to swap in an LLM call for more natural copy.

## Status
Prototype built for hackathon submission (deadline Nov 12, 2026). Next steps: wire real sandbox credentials, record demo video, deploy webhook endpoint publicly (e.g. on a small VPS or serverless function) for the PayPal webhook to reach.

## License
MIT
