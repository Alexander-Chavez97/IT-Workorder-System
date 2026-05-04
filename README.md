# City of Laredo IST — IT Work Order System

A web-based IT support ticketing system for City of Laredo employees to submit and track work orders. Built with Django.

🔗 **Live Site:** https://plasticshrimp.pythonanywhere.com

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
| Manage Employees | `/manage_employees/` |
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

Full access to everything IST Staff can access.

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
5. Fill in the **Additional Context** section — WHEN the issue started and WHY it is urgent are required.
6. Optionally attach up to 5 screenshots.
7. The system automatically assigns your ticket a priority, support team, and SLA deadline.

### Tracking a Ticket

Go to **Track Ticket** in the nav bar and enter your ticket reference number (e.g. `TKT-0042`). You can see the current status, assigned team, priority, SLA, and any screenshots attached.

### Admin Queue (IST and Admin only)

The admin queue shows all tickets across all departments. You can filter by status, priority, or department tier. Click any ticket to view full details, add internal notes, escalate the priority, resolve it, or upload additional screenshots.

### Manage Employees (IST and Admin only)

View all IST staff and admin accounts, filter by role and status, view individual employee ticket history, and export the employee list as CSV, XLSX, or PDF.

### Exporting Reports (IST and Admin only)

Use the CSV, XLSX, or PDF buttons above the queue table. Exports respect whatever filters are currently active.

---

## How Routing Works

When a ticket is submitted it passes through four automatic checks:

**1. Department Tier** — Utilities, Police, Fire, Traffic Safety, and Bridges are Critical Infrastructure with tighter SLAs and higher priority floors. City Manager offices are Executive. Health departments are Public Safety. Everything else is Standard.

**2. Category → Team** — The category maps to a specific support team automatically. Network, server, and security tickets from Critical Infrastructure departments are forced to Critical (P1).

**3. Sub-Type** — Some sub-types escalate priority (Complete Outage bumps up). Others cap it (Password Reset is capped at Medium).

**4. Keyword Detection** — The description is scanned for trigger words like "outage," "SCADA," "entire department," and "emergency." Spelling errors are tolerated — "emergancy" still triggers the same as "emergency."

---

## Security Features

- **Login rate limiting** — accounts lock for 1 hour after 5 failed login attempts
- **Input sanitization** — HTML tags are stripped from all free-text fields before saving
- **File upload validation** — screenshots are verified as real images using Pillow before being saved
- **Security headers** — protections against clickjacking, MIME sniffing, and session hijacking

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

|              |                                  |
| ------------ | -------------------------------- |
| Backend      | Django 4.2                       |
| Database     | SQLite (local)                   |
| Hosting      | PythonAnywhere                   |
| Static files | WhiteNoise                       |
| Exports      | openpyxl (XLSX), reportlab (PDF) |
| Security     | django-axes, Pillow              |

---

## Project Structure

```
laredo_ist/
├── tickets/
│   ├── routing.py              ← 4-tier routing engine
│   ├── models.py               ← Employee, Ticket, TicketHistory, TicketAttachment
│   ├── views.py                ← controllers, auth, exports
│   ├── forms.py                ← ticket submission form with 5 W's
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
│       ├── manage_employees.html
│       ├── employee_detail.html
│       └── base.html
├── laredo_ist/
│   ├── settings.py
│   └── settings_production.py
└── requirements.txt
```

---

> TAMIU Computer Science — City of Laredo IST Capstone Project
