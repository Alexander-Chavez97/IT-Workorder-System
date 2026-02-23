# City of Laredo IST — IT Work Order System

A web-based IT support ticketing system for city employees to submit and track work orders. Built with Django and deployed on Railway.

🔗 **Live Site:** https://web-production-7049b.up.railway.app/

---

## What It Does

- Employees log in with their city ID, email, and password
- A **4-tier routing engine** automatically assigns priority, support team, and SLA target based on department, issue type, and keywords in the description
- Admins monitor the queue, escalate tickets, and export reports

---

## Using the System

### Employee Login

Go to the live site and sign in with your city credentials.

Test account:

```
Employee ID:  LRD-1001
Email:        m.gonzalez@laredotx.gov
Password:     Laredo2024!
```

### Pages

| URL                   | Description                      |
| --------------------- | -------------------------------- |
| `/`                   | Submit a ticket                  |
| `/admin-queue/`       | View and manage all tickets      |
| `/ticket/<ID>/`       | Ticket detail, escalate, resolve |
| `/routing-reference/` | How the routing engine works     |
| `/admin/`             | Django admin panel               |

---

## How Routing Works

Every ticket passes through 4 tiers before being assigned:

1. **Department tier** — Police/Fire/Utilities get tighter SLAs and higher priority floors than standard departments
2. **Category → Team** — e.g. `network` tickets from Critical Infrastructure go to NOC On-Call and auto-escalate to Critical (P1)
3. **Sub-type modifier** — e.g. `complete_outage` bumps priority; `pw_reset` is capped at Medium
4. **Keyword detection** — scans the description for words like `SCADA`, `outage`, `entire dept` and adjusts priority accordingly. Tolerant of common spelling errors.

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
python manage.py migrate
python manage.py seed_employees   # creates 20 test employees + sample tickets

# Start server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`

---

## Tech Stack

|                       |                                  |
| --------------------- | -------------------------------- |
| Backend               | Django 4.2                       |
| Database (local)      | SQLite                           |
| Database (production) | PostgreSQL via Railway           |
| Static files          | WhiteNoise                       |
| Server                | Gunicorn                         |
| Exports               | openpyxl (XLSX), reportlab (PDF) |

---

## Project Structure

```
laredo_ist/
├── tickets/
│   ├── routing.py        ← routing engine (no Django dependencies)
│   ├── models.py         ← Employee + Ticket models
│   ├── views.py          ← controllers + export endpoints
│   ├── forms.py
│   ├── urls.py
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── seed_employees.py
│   └── templates/tickets/
│       ├── login.html
│       ├── submit.html
│       ├── admin_queue.html
│       ├── ticket_detail.html
│       └── routing_ref.html
├── laredo_ist/
│   ├── settings.py             ← base (local dev)
│   └── settings_production.py ← production (Railway)
├── Dockerfile
├── Procfile
└── requirements.txt
```

---

> TAMIU Computer Science — City of Laredo IST Capstone Project
