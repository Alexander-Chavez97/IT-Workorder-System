# 🏛️ Laredo IST — IT Work Order System

> A Django MVC prototype for the **City of Laredo Information Systems & Technology** department.  
> Built for internal staff to self-submit IT support tickets, with an intelligent hierarchical routing engine that automatically assigns priority and team based on department, issue type, and content.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [MVC Architecture](#-mvc-architecture)
- [Routing Engine](#-routing-engine)
- [Getting Started](#-getting-started)
- [Available Pages](#-available-pages)
- [Database Configuration](#-database-configuration)
- [Using the Routing Engine Standalone](#-using-the-routing-engine-standalone)
- [PHP Migration Notes](#-php-migration-notes)
- [Tech Stack](#-tech-stack)

---

## 📌 Overview

The Laredo IST Work Order System allows city employees to submit IT support tickets through a web form. Submitted tickets are automatically analyzed by a **4-tier routing engine** that determines:

- The correct **support team** to assign
- The **effective priority** (which may be higher than what the user selected)
- The **SLA target** response time
- The **escalation path** from L1 Intake up to the IT Director or City Manager

The system is built as a **Django MVC prototype** demonstrating clean separation of concerns, with the routing logic fully decoupled from the web framework.

---

## ✨ Features

- 📝 **Employee submission form** with live routing preview — updates as you type via AJAX, no page reload
- ⚡ **4-tier hierarchical routing engine** — fully standalone Python module with zero Django dependencies
- 🔔 **Auto-priority adjustment** — the engine can escalate beyond what the user selected, with a plain-English explanation of every rule applied
- 📊 **Admin queue dashboard** with filtering by status, priority, and department tier
- 🎫 **Ticket detail view** with escalate and resolve actions
- 📖 **Live routing reference page** rendered directly from `routing.py` constants — documentation never goes out of sync
- 🗄️ **Django admin panel** for full database management out of the box
- 🔌 **AJAX endpoint** (`/api/route/`) serving the live form preview

---

## 📁 Project Structure

```
laredo_ist/
│
├── manage.py                          # Django management entry point
├── requirements.txt                   # Python dependencies
├── README.md
│
├── laredo_ist/                        # Project-level configuration
│   ├── settings.py                    # Django settings (database, apps, timezone)
│   ├── urls.py                        # Root URL dispatcher
│   └── wsgi.py                        # WSGI entry point for deployment
│
└── tickets/                           # Main application
    │
    ├── routing.py          ★          # Routing engine — zero Django dependencies
    ├── models.py                      # Ticket database model + computed properties
    ├── forms.py                       # Submission form (choices sourced from routing.py)
    ├── views.py                       # HTTP controllers — wires Model ↔ Template
    ├── urls.py                        # App-level URL patterns
    ├── admin.py                       # Django admin panel configuration
    ├── apps.py                        # App config
    │
    ├── migrations/
    │   └── 0001_initial.py            # Initial database schema migration
    │
    └── templates/tickets/
        ├── base.html                  # Shared layout, navigation & full CSS design system
        ├── submit.html                # Employee ticket submission page
        ├── success.html               # Post-submission confirmation
        ├── admin_queue.html           # Admin ticket dashboard with filters
        ├── ticket_detail.html         # Single ticket detail + escalate/resolve actions
        └── routing_ref.html           # Live routing logic reference (auto-generated from routing.py)
```

> **★** `routing.py` is the core of this project. It holds all business logic and contains no Django imports, making it independently testable and portable.

---

## 🏗️ MVC Architecture

This project follows a strict **Model–View–Controller** pattern, with clear boundaries between each layer.

| Layer          | Files                      | Responsibility                                                                               |
| -------------- | -------------------------- | -------------------------------------------------------------------------------------------- |
| **Model**      | `routing.py`, `models.py`  | All business logic, routing decisions, and database schema. Zero UI code.                    |
| **View**       | `templates/tickets/*.html` | Rendering only. Templates receive a context dictionary and display it — no logic lives here. |
| **Controller** | `views.py`, `urls.py`      | Receives HTTP requests, calls the Model, passes results to the correct View.                 |

### Why `routing.py` is kept separate

`routing.py` has **no Django imports**. It is a plain Python module that accepts plain inputs and returns a `RoutingResult` dataclass. This design means:

- ✅ Unit-testable without a running Django server
- ✅ Callable from a CLI script, a cron job, or a management command
- ✅ Portable to Flask, FastAPI, or any other framework without rewriting logic
- ✅ The routing reference page (`/routing-reference/`) renders directly from its constants — no chance of documentation drifting out of sync with the actual rules

---

## ⚙️ Routing Engine

Tickets pass through **four sequential tiers**. Each tier can only raise the effective priority — it can never lower what a previous tier already set.

---

### Tier 1 — Department Classification

Every department is pre-classified into one of four tiers before any other factor is considered. This is the most impactful modifier.

| Tier                           | Departments                                        | Priority Floor      | SLA Factor                    |
| ------------------------------ | -------------------------------------------------- | ------------------- | ----------------------------- |
| 🔴 **Critical Infrastructure** | Police, Fire, Utilities                            | P2 (High) minimum   | ×0.5 — half the baseline time |
| 🟡 **Executive**               | City Manager's Office                              | P2 (High) minimum   | ×0.5                          |
| 🟣 **Public Safety Support**   | Health Department                                  | P3 (Medium) minimum | ×0.75                         |
| ⚪ **Standard**                | Finance, Public Works, Parks, City Clerk, Planning | No floor            | ×1.0 baseline                 |

> **Example:** A Finance employee submitting a Medium ticket stays at Medium. A Police officer submitting the exact same ticket is automatically elevated to High.

---

### Tier 2 — Category → Team Assignment

The ticket category determines which team handles it. Three categories auto-escalate to **Critical (P1)** when coming from a Critical Infrastructure department.

| Category   | Standard Team                  | Critical Infra Team            | Auto-P1 for CI? |
| ---------- | ------------------------------ | ------------------------------ | :-------------: |
| `hardware` | Desktop Support Team           | Field Tech Unit                |        —        |
| `software` | Application Support Team       | Application Support Team       |        —        |
| `network`  | Network Operations Team        | NOC On-Call                    |       ✅        |
| `email`    | Messaging & Collaboration Team | Messaging & Collaboration Team |        —        |
| `security` | Security & Identity Team       | Security & Identity Team       |       ✅        |
| `phone`    | Telecom & VOIP Team            | Telecom & VOIP Team            |        —        |
| `server`   | Infrastructure & DBA Team      | Infrastructure & DBA Team      |       ✅        |
| `data`     | Infrastructure & DBA Team      | Infrastructure & DBA Team      |        —        |

---

### Tier 3 — Sub-Type Modifiers

The selected sub-type applies additional rules on top of the Tier 1 and 2 results.

| Sub-Type                  | Effect                                                                         |
| ------------------------- | ------------------------------------------------------------------------------ |
| `complete_outage`         | Force P1 on Critical Infra depts; +1 bump for all others                       |
| `no_internet`, `no_login` | Force P1 on Critical Infra; +1 bump for others                                 |
| `data_loss`               | +1 priority bump for all departments                                           |
| `pw_reset`, `new_user`    | **Capped at P3 (Medium)** for non-Infra depts — these are non-urgent workflows |

---

### Tier 4 — Keyword Detection

The ticket summary and description fields are scanned for keywords. This tier can override all previous tiers.

| Keywords                                        | Effect                                      |
| ----------------------------------------------- | ------------------------------------------- |
| `scada`, `dispatch`, `911`, `cad`               | **Force P1** — mission-critical city system |
| `everyone`, `entire dept`, `city-wide`          | **Force P1** — widespread impact detected   |
| `outage`, `offline`, `not working`, `no access` | +1 priority bump                            |
| `urgent`, `asap`, `emergency`                   | +1 priority bump                            |

---

### SLA Response Time Matrix

| Dept Tier                  | P1 Critical | P2 High | P3 Medium | P4 Low |
| -------------------------- | :---------: | :-----: | :-------: | :----: |
| 🔴 Critical Infrastructure |    1 hr     |  2 hrs  |   4 hrs   | 1 day  |
| 🟡 Executive               |    1 hr     |  2 hrs  |   4 hrs   | 1 day  |
| 🟣 Public Safety Support   |    2 hrs    |  4 hrs  |   8 hrs   | 2 days |
| ⚪ Standard                |    4 hrs    |  8 hrs  |   1 day   | 3 days |

---

## 🚀 Getting Started

### Prerequisites

- Python **3.11** or higher
- pip

### Installation

**1. Navigate into the project directory:**

```bash
cd laredo_ist
```

**2. Create and activate a virtual environment** _(recommended):_

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Run database migrations:**

```bash
python manage.py migrate
```

> This creates `db.sqlite3` and builds the `tickets_ticket` table. Only needs to be run once (or when models change).

**5. (Optional) Create a Django admin superuser:**

```bash
python manage.py createsuperuser
```

**6. Start the development server:**

```bash
python manage.py runserver
```

The app is now running at **http://127.0.0.1:8000/**

---

## 🌐 Available Pages

| URL                                        | Description                                                   |
| ------------------------------------------ | ------------------------------------------------------------- |
| `http://127.0.0.1:8000/`                   | Employee ticket submission form                               |
| `http://127.0.0.1:8000/admin-queue/`       | Admin dashboard — view, filter, and manage all tickets        |
| `http://127.0.0.1:8000/ticket/<ID>/`       | Individual ticket detail with escalate and resolve actions    |
| `http://127.0.0.1:8000/routing-reference/` | Live routing logic documentation (rendered from `routing.py`) |
| `http://127.0.0.1:8000/admin/`             | Django built-in admin panel                                   |
| `http://127.0.0.1:8000/api/route/`         | AJAX routing endpoint used by the submission form             |

---

## 🗄️ Database Configuration

SQLite is used by default and requires zero configuration. To switch to a production-grade database, update the `DATABASES` setting in `laredo_ist/settings.py`:

**PostgreSQL:**

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'laredo_ist',
        'USER': 'ist_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

```bash
pip install psycopg2-binary
```

**MySQL / MariaDB** _(common in existing city infrastructure):_

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'laredo_ist',
        'USER': 'ist_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

```bash
pip install mysqlclient
```

After switching databases, re-run `python manage.py migrate`.

---

## 🧪 Using the Routing Engine Standalone

Because `routing.py` has no Django dependencies, it can be run and tested without any web server:

```python
from tickets.routing import RoutingEngine

result = RoutingEngine.compute(
    dept="Police Department",
    category="network",
    subtype="complete_outage",
    user_priority=3,            # User selected: Medium
    text="Entire detective division has no internet access."
)

print(result.team)                # "NOC On-Call"
print(result.effective_priority)  # 1  ← auto-escalated to Critical
print(result.priority_label)      # "Critical"
print(result.sla)                 # "1 hr"
print(result.was_modified)        # True

for reason in result.reasons:
    print(reason)
# Tier 1 (Critical Infrastructure): priority elevated from Medium to High.
# Tier 2: 'network' on Critical Infrastructure dept — auto-escalated to Critical (P1).
# Tier 3 (sub-type 'complete_outage'): forced P1 on Critical Infra.
# Tier 4: keyword 'entire' detected — forced Critical. (City/dept-wide impact)
```

---

## 🔄 PHP Migration Notes

Since the City of Laredo runs other systems in PHP, this architecture is designed to map directly if a rewrite is ever required:

| Django Component | PHP / Laravel Equivalent                                                      |
| ---------------- | ----------------------------------------------------------------------------- |
| `routing.py`     | `app/Services/RoutingEngine.php` — plain service class, no framework coupling |
| `models.py`      | Eloquent model `app/Models/Ticket.php`                                        |
| `views.py`       | Controllers in `app/Http/Controllers/`                                        |
| Django templates | Blade templates in `resources/views/`                                         |
| `migrations/`    | Laravel migrations in `database/migrations/`                                  |
| `urls.py`        | Route definitions in `routes/web.php`                                         |
| AJAX endpoint    | Laravel API route returning JSON                                              |

The routing engine is entirely self-contained — it is the first and easiest file to port. All four tiers can be reproduced as a single PHP class with no framework dependencies.

---

## 🛠️ Tech Stack

| Component                   | Technology                                     |
| --------------------------- | ---------------------------------------------- |
| Backend framework           | Django 4.2                                     |
| Language                    | Python 3.11+                                   |
| Database (development)      | SQLite 3                                       |
| Database (production-ready) | PostgreSQL or MySQL/MariaDB                    |
| Frontend                    | Django Templates + Vanilla JS                  |
| Fonts                       | IBM Plex Sans · IBM Plex Mono · IBM Plex Serif |
| Routing logic               | Custom 4-tier engine (`tickets/routing.py`)    |

---

> **Prototype developed for the City of Laredo IST Department.**  
> Texas A&M International University — Computer Science Capstone Project
