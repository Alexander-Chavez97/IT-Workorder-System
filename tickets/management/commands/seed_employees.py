"""
tickets/management/commands/seed_employees.py
=============================================
Populates the database with realistic fake employees and sample tickets.

Three roles are seeded:
  dept  — regular city department employees (submit & track tickets only)
  ist   — IST support staff (also see admin queue and ticket detail)
  admin — IST administrator (full access)

Usage:
    python manage.py seed_employees          # create if not exists
    python manage.py seed_employees --reset  # wipe and recreate
"""

import json
from django.core.management.base import BaseCommand

from tickets.models import Employee, EmployeeRole, Ticket, TicketStatus, TicketHistory, HistoryAction
from tickets.routing import RoutingEngine


# ---------------------------------------------------------------------------
# DEPARTMENT EMPLOYEES  (role: dept)
# ---------------------------------------------------------------------------

DEPT_EMPLOYEES = [
    # (employee_id, first, last, email, department, password)
    ("LRD-1001", "Maria",    "Gonzalez",  "m.gonzalez@laredotx.gov",  "Finance - Accounting",          "Laredo2024!"),
    ("LRD-1002", "Carlos",   "Ramirez",   "c.ramirez@laredotx.gov",   "Police Department",             "Laredo2024!"),
    ("LRD-1003", "Sofia",    "Herrera",   "s.herrera@laredotx.gov",   "City Secretary",                "Laredo2024!"),
    ("LRD-1004", "James",    "Williams",  "j.williams@laredotx.gov",  "Public Works",                  "Laredo2024!"),
    ("LRD-1005", "Ana",      "Torres",    "a.torres@laredotx.gov",    "Health Department",             "Laredo2024!"),
    ("LRD-1006", "Roberto",  "Salinas",   "r.salinas@laredotx.gov",   "Fire Department",               "Laredo2024!"),
    ("LRD-1007", "Linda",    "Martinez",  "l.martinez@laredotx.gov",  "Parks & Leisure - Haynes Recreation", "Laredo2024!"),
    ("LRD-1008", "David",    "Nguyen",    "d.nguyen@laredotx.gov",    "Utilities Department",          "Laredo2024!"),
    ("LRD-1009", "Patricia", "Lopez",     "p.lopez@laredotx.gov",     "Planning Department",           "Laredo2024!"),
    ("LRD-1010", "Miguel",   "Castillo",  "m.castillo@laredotx.gov",  "City Manager",                  "Laredo2024!"),
    ("LRD-1011", "Jessica",  "Flores",    "j.flores@laredotx.gov",    "Finance - Accounting",          "Laredo2024!"),
    ("LRD-1012", "Fernando", "Reyes",     "f.reyes@laredotx.gov",     "Police - Patrol",               "Laredo2024!"),
    ("LRD-1013", "Melissa",  "Garza",     "m.garza@laredotx.gov",     "Health - W.I.C.",               "Laredo2024!"),
    ("LRD-1014", "Steven",   "Morales",   "s.morales@laredotx.gov",   "Public Works",                  "Laredo2024!"),
    ("LRD-1015", "Diana",    "Vasquez",   "d.vasquez@laredotx.gov",   "City Secretary",                "Laredo2024!"),
    ("LRD-1016", "Hector",   "Jimenez",   "h.jimenez@laredotx.gov",   "Fire Department",               "Laredo2024!"),
    ("LRD-1017", "Rachel",   "Cruz",      "r.cruz@laredotx.gov",      "Parks & Leisure - Haynes Recreation", "Laredo2024!"),
    ("LRD-1018", "Antonio",  "Mendoza",   "a.mendoza@laredotx.gov",   "Utilities Department",          "Laredo2024!"),
    ("LRD-1019", "Vanessa",  "Perez",     "v.perez@laredotx.gov",     "Planning Department",           "Laredo2024!"),
    ("LRD-1020", "Eduardo",  "Ramos",     "e.ramos@laredotx.gov",     "City Manager",                  "Laredo2024!"),
    # Extra dept employees for variety
    ("LRD-1021", "Gloria",   "Sandoval",  "g.sandoval@laredotx.gov",  "Tax Department",                "Laredo2024!"),
    ("LRD-1022", "Marco",    "Delgado",   "m.delgado@laredotx.gov",   "Library - Main Branch",         "Laredo2024!"),
    ("LRD-1023", "Irene",    "Fuentes",   "i.fuentes@laredotx.gov",   "Health - Pharmacy",             "Laredo2024!"),
    ("LRD-1024", "Oscar",    "Medina",    "o.medina@laredotx.gov",    "Fleet Management",              "Laredo2024!"),
    ("LRD-1025", "Norma",    "Ibarra",    "n.ibarra@laredotx.gov",    "Municipal Court",               "Laredo2024!"),
    ("LRD-1026", "Ruben",    "Cantu",     "r.cantu@laredotx.gov",     "Traffic Safety",                "Laredo2024!"),
    ("LRD-1027", "Leticia",  "Vela",      "l.vela@laredotx.gov",      "Human Resources",               "Laredo2024!"),
    ("LRD-1028", "Jorge",    "Pena",      "j.pena@laredotx.gov",      "Building Development Services", "Laredo2024!"),
    ("LRD-1029", "Carmen",   "Trevino",   "c.trevino@laredotx.gov",   "Environmental Services",        "Laredo2024!"),
    ("LRD-1030", "Felipe",   "Aguilar",   "f.aguilar@laredotx.gov",   "Transit System - El Metro",     "Laredo2024!"),
]


# ---------------------------------------------------------------------------
# IST SUPPORT STAFF  (role: ist)
# ---------------------------------------------------------------------------

IST_EMPLOYEES = [
    # (employee_id, first, last, email, password)
    ("IST-1001", "Daniel",   "Ochoa",     "d.ochoa@laredotx.gov",     "ISTstaff2024!"),
    ("IST-1002", "Priscilla","Leal",      "p.leal@laredotx.gov",      "ISTstaff2024!"),
    ("IST-1003", "Marcus",   "Solis",     "m.solis@laredotx.gov",     "ISTstaff2024!"),
    ("IST-1004", "Samantha", "Guerra",    "s.guerra@laredotx.gov",    "ISTstaff2024!"),
    ("IST-1005", "Kevin",    "Dominguez", "k.dominguez@laredotx.gov", "ISTstaff2024!"),
    ("IST-1006", "Brenda",   "Villarreal","b.villarreal@laredotx.gov","ISTstaff2024!"),
]


# ---------------------------------------------------------------------------
# IST ADMINS  (role: admin)
# ---------------------------------------------------------------------------

ADMIN_EMPLOYEES = [
    # (employee_id, first, last, email, password)
    ("IST-ADMIN",  "IST",     "Admin",    "ist.admin@laredotx.gov",   "ISTadmin2024!"),
    ("IST-ADMIN2", "Roberto", "Cavazos",  "r.cavazos@laredotx.gov",   "ISTadmin2024!"),
]


# ---------------------------------------------------------------------------
# SAMPLE TICKETS
# ---------------------------------------------------------------------------

SAMPLE_TICKETS = [
    {
        "emp_id": "LRD-1001",
        "category": "hardware", "subtype": "no_boot", "issue_type": "wont_power_on",
        "title": "Desktop will not turn on after weekend",
        "description": "Computer was working fine Friday. Came in Monday and it won't power on at all.",
        "status": "In Progress",
    },
    {
        "emp_id": "LRD-1002",
        "category": "network", "subtype": "complete_outage", "issue_type": "dept_outage",
        "title": "Entire detective division has no network access",
        "description": "All computers on the 3rd floor lost internet and internal network access. Cannot access RMS or dispatch systems.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1003",
        "category": "email", "subtype": "no_login", "issue_type": "password_issue",
        "title": "Cannot log into Outlook — locked out",
        "description": "Getting account locked message when trying to open Outlook.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1007",
        "category": "software", "subtype": "app_crash", "issue_type": "app_freezes",
        "title": "Parks scheduling software crashes on launch",
        "description": "RecTrac crashes immediately after login screen since the update last Tuesday.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1018",
        "category": "security", "subtype": "data_loss", "issue_type": "suspected_breach",
        "title": "SCADA system showing unauthorized access alert",
        "description": "Water treatment SCADA console is showing an unauthorized access alert from an unknown IP.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1010",
        "category": "hardware", "subtype": "display", "issue_type": "no_display_output",
        "title": "Monitor not displaying anything after office move",
        "description": "Moved office over the weekend. Reconnected everything but monitor stays black.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1005",
        "category": "software", "subtype": "no_login", "issue_type": "account_locked",
        "title": "EMR system account locked — patients waiting",
        "description": "Cannot access Electronic Medical Records. Have patients in waiting room.",
        "status": "In Progress",
    },
    {
        "emp_id": "LRD-1011",
        "category": "data", "subtype": "data_loss", "issue_type": "report_wrong",
        "title": "Budget report showing wrong totals for Q3",
        "description": "Q3 budget summary report is showing totals that don't match our spreadsheets.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1021",
        "category": "software", "subtype": "no_login", "issue_type": "account_locked",
        "title": "Cannot log into tax processing system",
        "description": "My account shows as disabled when trying to log into the Tyler Technologies tax system.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1026",
        "category": "hardware", "subtype": "peripheral", "issue_type": "printer_issue",
        "title": "Traffic enforcement printer not working",
        "description": "The printer at the parking enforcement office won't connect. Last printed Friday.",
        "status": "Open",
    },
    {
        "emp_id": "LRD-1030",
        "category": "network", "subtype": "slow_conn", "issue_type": "slow_internet",
        "title": "El Metro admin office internet extremely slow",
        "description": "Internet has been very slow all week at the transit admin office. Affecting scheduling software.",
        "status": "Closed",
    },
    {
        "emp_id": "LRD-1016",
        "category": "hardware", "subtype": "no_boot", "issue_type": "boot_loop",
        "title": "Fire station laptop stuck in boot loop",
        "description": "Laptop at Station 1 keeps restarting. Started after Windows update last night.",
        "status": "In Progress",
    },
]


class Command(BaseCommand):
    help = "Seed the database with fake employees (dept, IST, admin) and sample tickets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing employees and tickets before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Ticket.objects.all().delete()
            Employee.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing employees and tickets."))

        created_dept = self._seed_group(DEPT_EMPLOYEES,  EmployeeRole.DEPT,  "Information Services & Technology")
        created_ist  = self._seed_group_ist(IST_EMPLOYEES, EmployeeRole.IST)
        created_adm  = self._seed_group_ist(ADMIN_EMPLOYEES, EmployeeRole.ADMIN)

        self.stdout.write(self.style.SUCCESS(
            f"  Dept employees:  {created_dept} created"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  IST employees:   {created_ist} created"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Admin accounts:  {created_adm} created"
        ))

        # Build lookup map for ticket creation
        emp_map = {e.employee_id: e for e in Employee.objects.all()}
        created_tix = self._seed_tickets(SAMPLE_TICKETS, emp_map)
        self.stdout.write(self.style.SUCCESS(f"  Tickets:         {created_tix} created"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("── Seed complete. Test credentials ──"))
        self.stdout.write("")
        self.stdout.write("  DEPT EMPLOYEES (submit + track only)")
        self.stdout.write("    Any LRD-10xx / their email / Laredo2024!")
        self.stdout.write("    Example: LRD-1001 / m.gonzalez@laredotx.gov / Laredo2024!")
        self.stdout.write("")
        self.stdout.write("  IST STAFF (+ admin queue + ticket detail)")
        self.stdout.write("    Any IST-10xx / their email / ISTstaff2024!")
        self.stdout.write("    Example: IST-1001 / d.ochoa@laredotx.gov / ISTstaff2024!")
        self.stdout.write("")
        self.stdout.write("  IST ADMIN (full access)")
        self.stdout.write("    IST-ADMIN  / ist.admin@laredotx.gov  / ISTadmin2024!")
        self.stdout.write("    IST-ADMIN2 / r.cavazos@laredotx.gov  / ISTadmin2024!")

    def _seed_group(self, employees, role, department):
        count = 0
        for emp_id, first, last, email, dept, raw_pw in employees:
            emp, created = Employee.objects.get_or_create(
                employee_id=emp_id,
                defaults={
                    "first_name": first, "last_name": last,
                    "email": email, "department": dept, "role": role,
                },
            )
            if created:
                emp.set_password(raw_pw)
                emp.save()
                count += 1
            elif emp.role != role:
                emp.role = role
                emp.save()
        return count

    def _seed_group_ist(self, employees, role):
        count = 0
        for emp_id, first, last, email, raw_pw in employees:
            emp, created = Employee.objects.get_or_create(
                employee_id=emp_id,
                defaults={
                    "first_name": first, "last_name": last,
                    "email": email,
                    "department": "Information Services & Technology",
                    "role": role,
                },
            )
            if created:
                emp.set_password(raw_pw)
                emp.save()
                count += 1
            elif emp.role != role:
                emp.role = role
                emp.save()
        return count

    def _seed_tickets(self, tickets, emp_map):
        count = 0
        for t in tickets:
            emp = emp_map.get(t["emp_id"])
            if not emp:
                continue
            text   = t["title"] + " " + t["description"]
            result = RoutingEngine.compute(
                dept=emp.department,
                category=t["category"],
                subtype=t.get("subtype", ""),
                user_priority=3,
                text=text,
            )
            ticket = Ticket(
                submitter=emp,
                name=emp.full_name,
                employee_id=emp.employee_id,
                department=emp.department,
                email=emp.email,
                category=t["category"],
                subtype=t.get("subtype", ""),
                issue_type=t.get("issue_type", ""),
                title=t["title"],
                description=t["description"],
                user_priority=3,
                status=t["status"],
                routing_tier=result.tier,
                routing_tier_label=result.tier_label,
                routing_team=result.team,
                routing_sla=result.sla,
                routing_effective_priority=result.effective_priority,
                routing_was_modified=result.was_modified,
                routing_reasons=json.dumps(result.reasons),
                routing_escalation_path=json.dumps(result.escalation_path),
            )
            ticket.save()

            # ── Seed history for this ticket
            self._seed_history(ticket, t, result)

            count += 1
        return count

    def _seed_history(self, ticket, t, result):
        """Create realistic history entries for demo tickets."""
        ist_staff = [
            "Daniel Ochoa", "Priscilla Leal", "Marcus Solis",
            "Samantha Guerra", "Kevin Dominguez", "Brenda Villarreal",
        ]
        import random
        rng = random.Random(ticket.id)   # deterministic per ticket
        assignee = rng.choice(ist_staff)

        # Every ticket gets a Created entry
        TicketHistory.objects.create(
            ticket=ticket,
            action=HistoryAction.CREATED,
            changed_by=ticket.name,
            team_after=ticket.routing_team,
            priority_after=ticket.routing_effective_priority,
            note="Ticket submitted via self-service portal.",
        )

        # Tickets that are In Progress or Closed get an assignment note
        if ticket.status in ("In Progress", "Closed"):
            TicketHistory.objects.create(
                ticket=ticket,
                action=HistoryAction.ASSIGNED,
                changed_by="IST Admin",
                team_before="",
                team_after=ticket.routing_team,
                note=f"Assigned to {assignee} for investigation.",
            )

        # Some tickets get a working note
        notes_by_category = {
            "hardware":  "Technician remotely diagnosed the issue. Scheduling on-site visit to inspect hardware.",
            "network":   "NOC confirmed the outage. Tracing the fault to the distribution switch on floor 3.",
            "software":  "Reproduced the issue in test environment. Escalating to vendor support for patch.",
            "email":     "Account lockout confirmed in Active Directory. Coordinating with security team before unlock.",
            "security":  "Incident logged with cybersecurity team. Reviewing access logs and isolating affected systems.",
            "data":      "Running integrity check on the affected database tables. Initial review shows import mismatch.",
            "phone":     "Telecom team investigating the routing issue. Temporary workaround provided to user.",
        }
        if ticket.status in ("In Progress", "Closed") and rng.random() > 0.3:
            note_text = notes_by_category.get(
                ticket.category,
                "Issue under investigation. User notified of estimated resolution time."
            )
            TicketHistory.objects.create(
                ticket=ticket,
                action=HistoryAction.NOTE,
                changed_by=assignee,
                note=note_text,
            )

        # High or Critical tickets get an escalation entry
        if ticket.routing_effective_priority <= 2 and rng.random() > 0.4:
            pri_before = min(ticket.routing_effective_priority + 1, 4)
            TicketHistory.objects.create(
                ticket=ticket,
                action=HistoryAction.ESCALATED,
                changed_by="IST Admin",
                priority_before=pri_before,
                priority_after=ticket.routing_effective_priority,
                team_before=ticket.routing_team,
                team_after=ticket.routing_team,
                note="Priority raised due to operational impact.",
            )

        # Closed tickets get a resolution entry
        if ticket.status == "Closed":
            resolutions = {
                "hardware":  "Replaced faulty RAM module. System tested and confirmed stable.",
                "network":   "Faulty switch port identified and replaced. Network restored to full capacity.",
                "software":  "Vendor patch applied. Application tested and confirmed working.",
                "email":     "Account unlocked and MFA reset. User confirmed access restored.",
                "security":  "Threat contained. Access logs reviewed, no data exfiltration detected.",
                "data":      "Data re-imported from clean source. Report totals verified correct.",
                "phone":     "Phone routing reconfigured. Incoming calls confirmed working.",
            }
            resolution = resolutions.get(
                ticket.category,
                "Issue resolved. User confirmed system is working as expected."
            )
            TicketHistory.objects.create(
                ticket=ticket,
                action=HistoryAction.RESOLVED,
                changed_by=assignee,
                note=resolution,
            )