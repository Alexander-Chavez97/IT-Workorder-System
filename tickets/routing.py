"""
tickets/routing.py
==================
Hierarchical Routing Engine for the Laredo IST Work Order System.

This module is intentionally kept INDEPENDENT of Django — it has no imports
from models, views, or any Django module. It can be unit-tested in isolation,
reused in a CLI script, or ported to another framework without modification.

Four-Tier Routing Logic
-----------------------
Tier 1  Department Classification
        Assigns each department a tier that sets a priority floor and SLA
        multiplier before anything else is evaluated.

Tier 2  Category → Team Assignment
        Maps the ticket category to a support team. Critical Infrastructure
        departments receive specialized team overrides.

Tier 3  Sub-Type Modifier
        Sub-type choices can bump priority upward, force escalation for
        specific tiers, or cap priority downward (e.g. onboarding tickets).

Tier 4  Keyword Detection
        Free-text fields (summary + description) are scanned for keywords
        that signal broader impact or mission-critical systems, triggering
        automatic escalation.

Public API
----------
    result = RoutingEngine.compute(dept, category, subtype, user_priority, text)
    # Returns a RoutingResult dataclass with all routing decisions and reasons.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# TIER 1 — DEPARTMENT CLASSIFICATION
# ---------------------------------------------------------------------------

class DeptTier:
    CRITICAL_INFRA = "CRITICAL_INFRA"
    EXECUTIVE      = "EXECUTIVE"
    PUBLIC_SAFETY  = "PUBLIC_SAFETY"
    STANDARD       = "STANDARD"


# Maps every department name to its tier.
DEPARTMENT_TIERS: dict[str, str] = {
    "Police Department":     DeptTier.CRITICAL_INFRA,
    "Fire Department":       DeptTier.CRITICAL_INFRA,
    "Utilities":             DeptTier.CRITICAL_INFRA,
    "City Manager's Office": DeptTier.EXECUTIVE,
    "Health Department":     DeptTier.PUBLIC_SAFETY,
    "Finance":               DeptTier.STANDARD,
    "Public Works":          DeptTier.STANDARD,
    "Parks & Recreation":    DeptTier.STANDARD,
    "City Clerk":            DeptTier.STANDARD,
    "Planning & Zoning":     DeptTier.STANDARD,
}

# Metadata for each tier: label, priority floor, SLA factor, display color.
TIER_META: dict[str, dict] = {
    DeptTier.CRITICAL_INFRA: {
        "label":         "Critical Infrastructure",
        "priority_floor": 2,       # minimum effective priority (1=Critical, 4=Low)
        "sla_factor":    0.5,      # SLA tightened to 50% of baseline
        "color":         "red",
        "icon":          "🔴",
    },
    DeptTier.EXECUTIVE: {
        "label":         "Executive",
        "priority_floor": 2,
        "sla_factor":    0.5,
        "color":         "gold",
        "icon":          "🟡",
    },
    DeptTier.PUBLIC_SAFETY: {
        "label":         "Public Safety Support",
        "priority_floor": 3,
        "sla_factor":    0.75,
        "color":         "purple",
        "icon":          "🟣",
    },
    DeptTier.STANDARD: {
        "label":         "Standard",
        "priority_floor": 4,       # no floor; user selection is authoritative
        "sla_factor":    1.0,
        "color":         "steel",
        "icon":          "⚪",
    },
}


# ---------------------------------------------------------------------------
# TIER 2 — CATEGORY → TEAM MAPPING
# ---------------------------------------------------------------------------

# Categories where Critical Infra depts auto-escalate to P1.
CRITICAL_INFRA_P1_CATEGORIES = {"network", "server", "security"}

# Maps category slug → standard team and Critical Infra override team.
CATEGORY_TEAMS: dict[str, dict[str, str]] = {
    "hardware": {
        "standard": "Desktop Support Team",
        "critical_infra": "Field Tech Unit (Priority Response)",
    },
    "software": {
        "standard": "Application Support Team",
        "critical_infra": "Application Support Team",
    },
    "network": {
        "standard": "Network Operations Team",
        "critical_infra": "NOC On-Call",
    },
    "email": {
        "standard": "Messaging & Collaboration Team",
        "critical_infra": "Messaging & Collaboration Team",
    },
    "security": {
        "standard": "Security & Identity Team",
        "critical_infra": "Security & Identity Team",
    },
    "phone": {
        "standard": "Telecom & VOIP Team",
        "critical_infra": "Telecom & VOIP Team",
    },
    "server": {
        "standard": "Infrastructure & DBA Team",
        "critical_infra": "Infrastructure & DBA Team",
    },
    "data": {
        "standard": "Infrastructure & DBA Team",
        "critical_infra": "Infrastructure & DBA Team",
    },
}


# ---------------------------------------------------------------------------
# TIER 3 — SUB-TYPE MODIFIERS
# ---------------------------------------------------------------------------

# Each entry: priority_bump (raise by N levels), ci_force_p1 (force P1 on
# Critical Infra), priority_cap (clamp DOWN to this value for non-Infra depts).
SUBTYPE_RULES: dict[str, dict] = {
    "complete_outage": {"bump": 1, "ci_force_p1": True,  "cap": None},
    "no_internet":     {"bump": 1, "ci_force_p1": True,  "cap": None},
    "no_login":        {"bump": 1, "ci_force_p1": True,  "cap": None},
    "data_loss":       {"bump": 1, "ci_force_p1": False, "cap": None},
    "no_boot":         {"bump": 0, "ci_force_p1": False, "cap": None},
    "app_crash":       {"bump": 0, "ci_force_p1": False, "cap": None},
    "pw_reset":        {"bump": 0, "ci_force_p1": False, "cap": 3},    # cap at Medium
    "new_user":        {"bump": 0, "ci_force_p1": False, "cap": 3},    # onboarding, non-urgent
    "slow":            {"bump": 0, "ci_force_p1": False, "cap": None},
    "display":         {"bump": 0, "ci_force_p1": False, "cap": None},
    "peripheral":      {"bump": 0, "ci_force_p1": False, "cap": None},
    "slow_conn":       {"bump": 0, "ci_force_p1": False, "cap": None},
}


# ---------------------------------------------------------------------------
# TIER 4 — KEYWORD DETECTION
# ---------------------------------------------------------------------------

# Each rule: list of trigger keywords, optional force (hard-set priority),
# optional bump (raise by N), and a human-readable note.
KEYWORD_RULES: list[dict] = [
    {
        "keywords": ["scada", "dispatch", "911", " cad ", "computer aided dispatch"],
        "force": 1,
        "bump":  None,
        "note":  "Mission-critical system keyword detected (SCADA / 911 / CAD)",
    },
    {
        "keywords": [
            "everyone", "entire department", "entire dept",
            "all users", "city-wide", "citywide", "entire building",
            "entire division",
        ],
        "force": 1,
        "bump":  None,
        "note":  "City/department-wide impact keywords detected",
    },
    {
        "keywords": [
            "outage", "completely down", "totally down",
            "not working at all", "offline", "no access", "cannot access",
        ],
        "force": None,
        "bump":  1,
        "note":  "Outage-level keyword detected",
    },
    {
        "keywords": ["urgent", "asap", "emergency", "immediately"],
        "force": None,
        "bump":  1,
        "note":  "Urgency keyword detected in description",
    },
]


# ---------------------------------------------------------------------------
# SLA MATRIX
# ---------------------------------------------------------------------------

# [dept_tier][priority_level] → SLA string
SLA_MATRIX: dict[str, dict[int, str]] = {
    DeptTier.CRITICAL_INFRA: {1: "1 hr",  2: "2 hrs", 3: "4 hrs",  4: "1 day"},
    DeptTier.EXECUTIVE:      {1: "1 hr",  2: "2 hrs", 3: "4 hrs",  4: "1 day"},
    DeptTier.PUBLIC_SAFETY:  {1: "2 hrs", 2: "4 hrs", 3: "8 hrs",  4: "2 days"},
    DeptTier.STANDARD:       {1: "4 hrs", 2: "8 hrs", 3: "1 day",  4: "3 days"},
}


# ---------------------------------------------------------------------------
# ESCALATION PATHS
# ---------------------------------------------------------------------------

ESCALATION_PATHS: dict[int, list[str]] = {
    1: ["L1 Intake", "Team Lead", "IT Director", "City Manager"],
    2: ["L1 Intake", "L2 Specialist", "Team Lead"],
    3: ["L1 Intake", "L2 Specialist"],
    4: ["L1 Intake"],
}

PRIORITY_LABELS: dict[int, str] = {
    1: "Critical",
    2: "High",
    3: "Medium",
    4: "Low",
}


# ---------------------------------------------------------------------------
# RESULT DATACLASS
# ---------------------------------------------------------------------------

@dataclass
class RoutingResult:
    """
    Fully resolved routing decision returned by RoutingEngine.compute().

    Fields
    ------
    tier            Department tier slug (e.g. 'CRITICAL_INFRA').
    tier_label      Human-readable tier name.
    tier_icon       Emoji icon for the tier.
    tier_color      CSS color hint for the UI.
    team            Name of the assigned support team.
    sla             SLA string (e.g. '2 hrs').
    effective_priority  Final computed priority (1–4).
    user_priority       Priority selected by the user before engine adjustments.
    suggested_priority  Priority the engine recommends highlighting in the UI.
    escalation_path     Ordered list of escalation steps.
    reasons         List of human-readable strings explaining each rule applied.
    was_modified    True if the engine changed the user's priority selection.
    """
    tier:               str
    tier_label:         str
    tier_icon:          str
    tier_color:         str
    team:               str
    sla:                str
    effective_priority: int
    user_priority:      int
    suggested_priority: int
    escalation_path:    list[str]
    reasons:            list[str] = field(default_factory=list)
    was_modified:       bool = False

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.effective_priority, "Unknown")

    @property
    def user_priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.user_priority, "Unknown")


# ---------------------------------------------------------------------------
# ROUTING ENGINE
# ---------------------------------------------------------------------------

class RoutingEngine:
    """
    Pure-Python routing engine. No Django dependencies.

    Usage:
        result = RoutingEngine.compute(
            dept="Police Department",
            category="network",
            subtype="complete_outage",
            user_priority=3,
            text="Entire detective division has no internet access."
        )
        print(result.team)             # "NOC On-Call"
        print(result.effective_priority)  # 1
        print(result.sla)              # "1 hr"
    """

    @staticmethod
    def get_dept_tier(dept: str) -> str:
        """Return the tier slug for a given department name."""
        return DEPARTMENT_TIERS.get(dept, DeptTier.STANDARD)

    @staticmethod
    def get_tier_meta(tier: str) -> dict:
        """Return the metadata dict for a given tier slug."""
        return TIER_META.get(tier, TIER_META[DeptTier.STANDARD])

    @staticmethod
    def compute(
        dept: str,
        category: str,
        subtype: Optional[str],
        user_priority: int,
        text: str = "",
    ) -> RoutingResult:
        """
        Run all four routing tiers and return a RoutingResult.

        Parameters
        ----------
        dept            Department name string.
        category        Category slug (e.g. 'hardware', 'network').
        subtype         Sub-type slug or empty string / None.
        user_priority   Priority the user selected (1–4; 1=Critical).
        text            Combined summary + description text for keyword scan.
        """
        reasons: list[str] = []
        ep = max(1, min(4, user_priority))   # clamp to valid range
        up = ep                              # original user selection

        # ── TIER 1: Department floor ──────────────────────────────────────
        tier = RoutingEngine.get_dept_tier(dept)
        meta = RoutingEngine.get_tier_meta(tier)
        floor = meta["priority_floor"]

        if floor < ep:
            reasons.append(
                f"Tier 1 ({meta['label']}): priority elevated from "
                f"{PRIORITY_LABELS[ep]} to {PRIORITY_LABELS[floor]}."
            )
            ep = floor

        # ── TIER 2: Category escalation for Critical Infra ────────────────
        if tier == DeptTier.CRITICAL_INFRA and category in CRITICAL_INFRA_P1_CATEGORIES:
            if ep > 1:
                reasons.append(
                    f"Tier 2: '{category}' on Critical Infrastructure dept "
                    f"— auto-escalated to Critical (P1)."
                )
                ep = 1

        # ── TIER 3: Sub-type modifier ─────────────────────────────────────
        rule = SUBTYPE_RULES.get(subtype or "")
        if rule:
            if rule["ci_force_p1"] and tier == DeptTier.CRITICAL_INFRA and ep > 1:
                reasons.append(
                    f"Tier 3 (sub-type '{subtype}'): complete outage on "
                    f"Critical Infra — forced Critical (P1)."
                )
                ep = 1
            elif rule["bump"] and (ep - rule["bump"]) >= 1 and (ep - rule["bump"]) < ep:
                bumped = ep - rule["bump"]
                reasons.append(
                    f"Tier 3 (sub-type '{subtype}'): "
                    f"+{rule['bump']} priority bump → {PRIORITY_LABELS[bumped]}."
                )
                ep = bumped

            # Cap downward (e.g. password reset, new user onboarding)
            if rule["cap"] is not None and tier != DeptTier.CRITICAL_INFRA and ep < rule["cap"]:
                reasons.append(
                    f"Tier 3 (sub-type '{subtype}'): "
                    f"capped at {PRIORITY_LABELS[rule['cap']]} (non-urgent sub-type)."
                )
                ep = rule["cap"]

        # ── TIER 4: Keyword detection (exact + fuzzy spelling tolerance) ────
        combined = text.lower()
        words    = combined.split()   # token list for fuzzy matching

        for kw_rule in KEYWORD_RULES:
            matched_kw   = None
            matched_fuzzy = False

            for kw in kw_rule["keywords"]:
                # 1. Exact / substring match first (fast path)
                if kw in combined:
                    matched_kw = kw
                    break

                # 2. Fuzzy token match — each word vs keyword
                #    Only applied to single-word keywords (multi-word phrases
                #    are checked via substring above).
                if " " not in kw:
                    import difflib
                    close = difflib.get_close_matches(
                        kw, words, n=1, cutoff=0.82
                    )
                    if close:
                        matched_kw    = close[0]
                        matched_fuzzy = True
                        break

            if matched_kw:
                fuzzy_note = f" (fuzzy match for '{kw}')" if matched_fuzzy else ""
                if kw_rule["force"] is not None and ep > kw_rule["force"]:
                    reasons.append(
                        f"Tier 4: keyword '{matched_kw}'{fuzzy_note} detected "
                        f"— forced {PRIORITY_LABELS[kw_rule['force']]}. "
                        f"({kw_rule['note']})"
                    )
                    ep = kw_rule["force"]
                    break
                elif kw_rule["bump"] is not None:
                    bumped = max(1, ep - kw_rule["bump"])
                    if bumped < ep:
                        reasons.append(
                            f"Tier 4: keyword '{matched_kw}'{fuzzy_note} detected "
                            f"— bumped to {PRIORITY_LABELS[bumped]}. "
                            f"({kw_rule['note']})"
                        )
                        ep = bumped
                    break

        # ── TEAM ASSIGNMENT ───────────────────────────────────────────────
        cat_data = CATEGORY_TEAMS.get(category)
        if cat_data:
            team = (
                cat_data["critical_infra"]
                if tier == DeptTier.CRITICAL_INFRA
                else cat_data["standard"]
            )
        else:
            team = "General IST Queue"

        # ── FINAL SLA ─────────────────────────────────────────────────────
        sla = SLA_MATRIX.get(tier, SLA_MATRIX[DeptTier.STANDARD]).get(ep, "TBD")

        if not reasons:
            reasons.append(
                "All tiers evaluated with no modifications. "
                "Ticket routed by category with user-selected priority."
            )

        return RoutingResult(
            tier=tier,
            tier_label=meta["label"],
            tier_icon=meta["icon"],
            tier_color=meta["color"],
            team=team,
            sla=sla,
            effective_priority=ep,
            user_priority=up,
            suggested_priority=ep,
            escalation_path=ESCALATION_PATHS.get(ep, ESCALATION_PATHS[4]),
            reasons=reasons,
            was_modified=(ep != up),
        )


# ---------------------------------------------------------------------------
# HELPER: expose constants for template/form use
# ---------------------------------------------------------------------------

DEPARTMENT_CHOICES = [
    ("Police Department",     "Police Department"),
    ("Fire Department",       "Fire Department"),
    ("Utilities",             "Utilities"),
    ("City Manager's Office", "City Manager's Office"),
    ("Health Department",     "Health Department"),
    ("Finance",               "Finance"),
    ("Public Works",          "Public Works"),
    ("Parks & Recreation",    "Parks & Recreation"),
    ("City Clerk",            "City Clerk"),
    ("Planning & Zoning",     "Planning & Zoning"),
]

CATEGORY_CHOICES = [
    ("hardware", "Hardware — Computers, Printers, Devices"),
    ("software", "Software — Applications, Licenses, OS"),
    ("network",  "Network — Connectivity, WiFi, VPN"),
    ("email",    "Email & Communication"),
    ("security", "Security — Passwords, Access, Accounts"),
    ("phone",    "Phone / VOIP Systems"),
    ("server",   "Servers & Infrastructure"),
    ("data",     "Data & Reporting"),
]

PRIORITY_CHOICES = [
    (4, "Low — Minor issue, no work stoppage"),
    (3, "Medium — Workaround exists, productivity affected"),
    (2, "High — Work is halted, team affected"),
    (1, "Critical — System down, department or city-wide"),
]

# ---------------------------------------------------------------------------
# 3-LEVEL CASCADE: Category → Sub-Type → Issue Type
#
# Structure:
#   ISSUE_CASCADE[category] = {
#       "subtypes": [(slug, label), ...],
#       "issue_types": {
#           subtype_slug: [(slug, label), ...],
#       }
#   }
#
# This single source of truth is consumed by:
#   - forms.py (for model field choices)
#   - views.py (serialised to JSON for the JS cascade)
#   - routing.py compute() (issue_type passed in for extra context)
# ---------------------------------------------------------------------------

ISSUE_CASCADE: dict[str, dict] = {

    "hardware": {
        "subtypes": [
            ("no_boot",        "Not turning on / won't boot"),
            ("slow",           "Slow performance / intermittent"),
            ("display",        "Display or monitor issue"),
            ("peripheral",     "Peripheral device not working"),
            ("complete_outage","Complete hardware failure"),
        ],
        "issue_types": {
            "no_boot": [
                ("power_no_response", "No power — no lights, no fan, no response"),
                ("bios_error",        "BIOS or POST error displayed on screen"),
                ("os_wont_load",      "Reaches login screen but OS won't finish loading"),
                ("bootloop",          "Device restarts repeatedly / bootloop"),
            ],
            "slow": [
                ("high_cpu",          "Very slow — fan loud, likely high CPU/RAM"),
                ("low_storage",       "Low disk space warning shown"),
                ("slow_after_update", "Became slow after a recent update"),
                ("malware_suspected", "Unusual behavior / possible malware"),
            ],
            "display": [
                ("no_signal",         "Monitor shows 'No Signal' or stays black"),
                ("flickering",        "Screen flickering or flashing"),
                ("wrong_resolution",  "Wrong resolution / display stretched or cut off"),
                ("dead_pixels",       "Dead pixels or visible physical screen damage"),
            ],
            "peripheral": [
                ("printer_offline",   "Printer shows offline or won't print"),
                ("usb_not_recognized","USB device not recognized"),
                ("keyboard_mouse",    "Keyboard or mouse unresponsive"),
                ("external_drive",    "External drive not detected"),
            ],
            "complete_outage": [
                ("total_failure",     "Device completely unresponsive"),
                ("physical_damage",   "Physical damage observed"),
                ("powers_off",        "Powers on but immediately shuts off"),
            ],
        },
    },

    "software": {
        "subtypes": [
            ("app_crash",  "Application crash or error"),
            ("slow",       "Application running slowly"),
            ("no_login",   "Cannot log into application"),
            ("new_user",   "New install or access needed"),
            ("data_loss",  "File or data issue"),
        ],
        "issue_types": {
            "app_crash": [
                ("crash_on_launch",  "Crashes immediately when opening"),
                ("crash_during_use", "Crashes randomly during normal use"),
                ("error_code",       "Specific error code displayed"),
                ("freeze_hang",      "Freezes / becomes completely unresponsive"),
            ],
            "slow": [
                ("app_loading_slow", "Application takes very long to open"),
                ("browser_slow",     "Browser slow, freezing, or crashing"),
                ("print_queue_stuck","Print queue stuck or printing very slow"),
                ("db_query_slow",    "Database or query operations are slow"),
            ],
            "no_login": [
                ("license_expired",  "License expired or shows as invalid"),
                ("account_locked",   "Account locked inside the application"),
                ("not_activated",    "Software not activated on this machine"),
                ("wrong_credentials","Credentials not accepted / access denied"),
            ],
            "new_user": [
                ("install_needed",   "Software needs to be installed"),
                ("license_needed",   "License key or seat needed"),
                ("config_needed",    "Software needs configuration for this user"),
                ("access_needed",    "User needs access/permissions granted"),
            ],
            "data_loss": [
                ("file_missing",     "File or folder missing or accidentally deleted"),
                ("file_corrupted",   "File opens but data appears corrupted"),
                ("autosave_failed",  "Auto-save or backup did not run"),
                ("need_rollback",    "Need to restore a previous version of a file"),
            ],
        },
    },

    "network": {
        "subtypes": [
            ("no_internet",    "No internet or network access"),
            ("slow_conn",      "Slow or unstable connection"),
            ("complete_outage","Full network outage — multiple users"),
        ],
        "issue_types": {
            "no_internet": [
                ("no_connection",    "No network connection at all"),
                ("limited_conn",     "Limited / intermittent connection"),
                ("dns_failure",      "Connected but websites / resources won't load"),
                ("vpn_blocked",      "VPN not connecting or being blocked"),
            ],
            "slow_conn": [
                ("wifi_weak",        "WiFi signal weak in this area"),
                ("vpn_slow",         "VPN connected but very slow"),
                ("video_calls_poor", "Video calls or streaming buffering badly"),
                ("bandwidth_limit",  "Bandwidth seems throttled or limited"),
            ],
            "complete_outage": [
                ("floor_outage",     "Entire floor has no network access"),
                ("dept_outage",      "Entire department has no network access"),
                ("switch_down",      "Network switch or router appears to be down"),
                ("building_outage",  "Building-wide network outage"),
            ],
        },
    },

    "email": {
        "subtypes": [
            ("no_login",       "Cannot log into email"),
            ("slow",           "Email loading slowly or not syncing"),
            ("complete_outage","Cannot send or receive email"),
            ("new_user",       "New mailbox or access needed"),
        ],
        "issue_types": {
            "no_login": [
                ("password_issue",  "Cannot log in — password not accepted"),
                ("mfa_problem",     "Multi-factor authentication not working"),
                ("account_locked",  "Email account has been locked"),
                ("profile_missing", "Outlook profile missing or corrupted"),
            ],
            "slow": [
                ("inbox_loading",   "Inbox taking a long time to load"),
                ("attachments_slow","Attachments not loading or downloading"),
                ("sync_issue",      "Email not syncing across devices"),
                ("search_broken",   "Email search not returning results"),
            ],
            "complete_outage": [
                ("cannot_send",     "Can receive email but cannot send"),
                ("cannot_receive",  "Cannot receive any new emails"),
                ("outlook_crash",   "Outlook crashes on launch"),
                ("server_conn",     "Cannot connect to mail server at all"),
            ],
            "new_user": [
                ("new_mailbox",     "New email account / mailbox needed"),
                ("shared_mailbox",  "Access to a shared mailbox needed"),
                ("distro_list",     "Add user to a distribution list"),
                ("signature_setup", "Email signature setup or update needed"),
            ],
        },
    },

    "security": {
        "subtypes": [
            ("no_login", "Locked out of account or system"),
            ("pw_reset", "Password reset needed"),
            ("data_loss","Suspected security incident"),
            ("new_user", "New account or permissions needed"),
        ],
        "issue_types": {
            "no_login": [
                ("account_locked",   "Account locked after failed login attempts"),
                ("mfa_lost",         "Lost MFA device or authenticator app"),
                ("ad_account",       "Active Directory account issue"),
                ("vpn_credentials",  "VPN credentials not working"),
            ],
            "pw_reset": [
                ("forgot_password",  "Forgot password — need reset link"),
                ("expired_password", "Password expired and cannot be changed"),
                ("forced_reset_fail","Forced to reset but the reset page fails"),
                ("complexity_issue", "Password complexity requirements unclear"),
            ],
            "data_loss": [
                ("phishing_email",       "Received a suspicious or phishing email"),
                ("unauthorized_access",  "Possible unauthorized access to account"),
                ("malware_ransomware",   "Malware or ransomware detected/suspected"),
                ("potential_breach",     "Potential data breach or leak"),
            ],
            "new_user": [
                ("new_employee_account", "New employee account creation needed"),
                ("additional_perms",     "Additional permissions or roles needed"),
                ("vpn_setup",            "VPN access setup for new user"),
                ("system_access",        "Access to a specific system or application"),
            ],
        },
    },

    "phone": {
        "subtypes": [
            ("complete_outage","Phone completely not working"),
            ("slow",           "Call quality issues"),
            ("peripheral",     "Headset or phone hardware issue"),
        ],
        "issue_types": {
            "complete_outage": [
                ("no_dial_tone",    "No dial tone on desk phone"),
                ("phone_dead",      "Phone not powering on"),
                ("calls_not_routing","Calls not routing / going to wrong extension"),
                ("voicemail_issue", "Voicemail system not working"),
            ],
            "slow": [
                ("poor_call_quality","Call quality poor or distorted"),
                ("calls_dropping",  "Calls dropping frequently"),
                ("echo_feedback",   "Echo or feedback heard during calls"),
                ("call_delay",      "Noticeable delay / latency during calls"),
            ],
            "peripheral": [
                ("headset_not_working","Headset not working or not recognized"),
                ("conference_phone",  "Conference room phone issue"),
                ("handset_static",    "Handset producing static or crackling"),
                ("speakerphone",      "Speakerphone not functioning"),
            ],
        },
    },

    "server": {
        "subtypes": [
            ("complete_outage","Server or service is down"),
            ("slow",           "Server performance degraded"),
            ("data_loss",      "Data or storage concern"),
        ],
        "issue_types": {
            "complete_outage": [
                ("server_unreachable", "Server completely down / unreachable"),
                ("service_down",       "Specific service or application unreachable"),
                ("unplanned_downtime", "Unexpected downtime — not scheduled"),
                ("vm_not_starting",    "Virtual machine not starting"),
            ],
            "slow": [
                ("high_load",        "Server showing high CPU or memory load"),
                ("db_slow",          "Database queries running very slowly"),
                ("storage_nearly_full","Server storage nearly full"),
                ("network_latency",  "High network latency to this server"),
            ],
            "data_loss": [
                ("data_corrupted",   "Data on server appears corrupted"),
                ("backup_failed",    "Backup job failed or did not run"),
                ("accidental_delete","Files accidentally deleted from server"),
                ("raid_disk_alert",  "RAID array or disk health alert"),
            ],
        },
    },

    "data": {
        "subtypes": [
            ("data_loss","Report data is incorrect or missing"),
            ("slow",     "Reports or dashboards loading slowly"),
            ("app_crash","Reporting tool crashing or not working"),
        ],
        "issue_types": {
            "data_loss": [
                ("report_wrong",     "Report showing incorrect or unexpected data"),
                ("data_missing",     "Records or entire dataset is missing"),
                ("export_failed",    "Data export or download failing"),
                ("import_failed",    "Data import or upload failing"),
            ],
            "slow": [
                ("report_slow",      "Reports taking too long to generate"),
                ("dashboard_slow",   "Dashboard not loading or very slow"),
                ("query_timeout",    "Query timing out before completing"),
                ("export_slow",      "Data export taking excessively long"),
            ],
            "app_crash": [
                ("report_tool_crash","Reporting tool crashing"),
                ("bi_tool_issue",    "BI or analytics tool not opening/working"),
                ("connection_lost",  "Lost connection to data source"),
                ("scheduled_failed", "Scheduled report not running automatically"),
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# FLAT CHOICES LISTS — derived from ISSUE_CASCADE for model/form field validation
# ---------------------------------------------------------------------------

def _all_subtypes() -> list[tuple[str, str]]:
    """Flat list of every (slug, label) sub-type across all categories."""
    seen: dict[str, str] = {}
    for cat_data in ISSUE_CASCADE.values():
        for slug, label in cat_data["subtypes"]:
            seen[slug] = label
    return [("", "— Select sub-type —")] + list(seen.items())


def _all_issue_types() -> list[tuple[str, str]]:
    """Flat list of every (slug, label) issue type across all categories/subtypes."""
    seen: dict[str, str] = {}
    for cat_data in ISSUE_CASCADE.values():
        for issues in cat_data["issue_types"].values():
            for slug, label in issues:
                seen[slug] = label
    return [("", "— Select issue type —")] + list(seen.items())


SUBTYPE_CHOICES   = _all_subtypes()
ISSUE_TYPE_CHOICES = _all_issue_types()


# Convenience: category → valid subtype slugs (for JS cascade)
CATEGORY_SUBTYPES: dict[str, list[tuple[str, str]]] = {
    cat: data["subtypes"] for cat, data in ISSUE_CASCADE.items()
}

# Convenience: (category, subtype) → valid issue type slugs (for JS cascade)
SUBTYPE_ISSUE_TYPES: dict[str, dict[str, list[tuple[str, str]]]] = {
    cat: data["issue_types"] for cat, data in ISSUE_CASCADE.items()
}
