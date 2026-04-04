# City of Laredo IST — IT Work Order System

A web-based IT support ticketing system for City of Laredo employees to submit and track work orders. Built with Django and deployed on Render.

🔗 **Live Site:** https://laredo-ist.onrender.com

---

## Logging In

Navigate to the live site and sign in with your city credentials. There are three account types with different levels of access.

---

## Account Types & Access

### Department Employee

Regular city staff. Can submit tickets and track existing ones by reference number.

**Pages available:**
| Page | URL |
|------|-----|
| Submit a Work Order | `/` |
| Track a Ticket | `/track/` |

**Test credentials:**

```
Employee ID:  LRD-1001
Email:        m.gonzalez@laredotx.gov
Password:     Laredo2024!
```

All department employees share the same password: `Laredo2024!`
Full list of employee IDs: LRD-1001 through LRD-1030.

---

### IST Staff

Information Systems & Technology support staff. Has all department employee access plus the ability to view and manage the full ticket queue, add notes, escalate and resolve tickets, and export reports.

**Pages available:**
| Page | URL |
|------|-----|
| Submit a Work Order | `/` |
| Track a Ticket | `/track/` |
| Admin Queue | `/admin-queue/` |
| Ticket Detail | `/ticket/<ID>/` |
| Export CSV | `/export/csv/` |
| Export XLSX | `/export/xlsx/` |
| Export PDF | `/export/pdf/` |

**Test credentials:**

```
Employee ID:  IST-1001
Email:        d.ochoa@laredotx.gov
Password:     ISTstaff2024!
```

All IST staff share the same password: `ISTstaff2024!`
Full list of IST employee IDs: IST-1001 through IST-1006.

---

### IST Admin

Full access to everything IST Staff can access. Intended for department administrators and supervisors.

**Test credentials:**

```
Employee ID:  IST-ADMIN
Email:        ist.admin@laredotx.gov
Password:     ISTadmin2024!
```

Second admin account:

```
Employee ID:  IST-ADMIN2
Email:        r.cavazos@laredotx.gov
Password:     ISTadmin2024!
```

---

## How the System Works

### Submitting a Ticket

1. Log in with your city credentials. Your name, employee ID, department, and email are pre-filled automatically.
2. Select a **Category** — the Sub-Type dropdown will populate with relevant options.
3. Select a **Sub-Type** — the Specific Issue dropdown will populate.
4. Select a **Specific Issue**, write a brief summary and description, then click Submit.
5. The system automatically assigns your ticket a priority, support team, and SLA deadline. You will see the full routing decision on the confirmation page.

### Tracking a Ticket

Go to **Track Ticket** in the nav bar and enter your ticket reference number (e.g. `TKT-0042`). You can see the current status, assigned team, priority, and the full routing decision.

### Admin Queue (IST and Admin only)

The admin queue shows all tickets across all departments. You can filter by status, priority, or department tier. Click any ticket to view full details, add internal notes, escalate the priority, or mark it resolved.

### Exporting Reports (IST and Admin only)

Use the CSV, XLSX, or PDF buttons above the queue table. Exports respect whatever filters are currently active — so if you filter to Critical open tickets, the export contains only those.

---

## How Routing Works

When a ticket is submitted it passes through four automatic checks:

**1. Department Tier** — The system classifies the submitting department. Utilities, Police, Fire, Traffic Safety, and Bridges are Critical Infrastructure and receive tighter SLAs and higher priority floors. City Manager offices are Executive. Health and public safety departments are Public Safety. Everything else is Standard.

**2. Category → Team** — The category maps to a specific support team. Network, server, and security tickets from Critical Infrastructure departments are automatically forced to Critical (P1).

**3. Sub-Type** — Some sub-types escalate priority (Complete Outage bumps up). Others cap it (Password Reset is capped at Medium regardless of department).

**4. Keyword Detection** — The description is scanned for trigger words like "outage," "SCADA," "entire department," and "emergency." Matches escalate priority automatically. Spelling errors are tolerated — "emergancy" still triggers the same as "emergency."

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
python manage.py migrate

# Create test users and sample tickets
python manage.py seed_employees

# Start server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`

To reset and reseed from scratch:

```bash
python manage.py seed_employees --reset
```

---

## Tech Stack

|                       |                                  |
| --------------------- | -------------------------------- |
| Backend               | Django 4.2                       |
| Database (local)      | SQLite                           |
| Database (production) | PostgreSQL via Render            |
| Static files          | WhiteNoise                       |
| Server                | Gunicorn                         |
| Exports               | openpyxl (XLSX), reportlab (PDF) |

---

## Project Structure

```
laredo_ist/
├── tickets/
│   ├── routing.py        ← 4-tier routing engine (no Django dependencies)
│   ├── models.py         ← Employee, Ticket, TicketHistory models
│   ├── views.py          ← controllers, auth decorators, export endpoints
│   ├── forms.py
│   ├── urls.py
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── seed_employees.py
│   └── templates/tickets/
│       ├── login.html
│       ├── submit.html
│       ├── success.html
│       ├── ticket_lookup.html
│       ├── admin_queue.html
│       ├── ticket_detail.html
│       └── base.html
├── laredo_ist/
│   ├── settings.py             ← base (local dev)
│   └── settings_production.py ← production (Render)
├── render.yaml
├── Dockerfile
├── Procfile
└── requirements.txt
```

---

> TAMIU Computer Science — City of Laredo IST Capstone Project
