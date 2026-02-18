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

        # ── TIER 4: Keyword detection ─────────────────────────────────────
        combined = text.lower()
        for kw_rule in KEYWORD_RULES:
            matched_kw = next(
                (kw for kw in kw_rule["keywords"] if kw in combined), None
            )
            if matched_kw:
                if kw_rule["force"] is not None and ep > kw_rule["force"]:
                    reasons.append(
                        f"Tier 4: keyword '{matched_kw}' detected "
                        f"— forced {PRIORITY_LABELS[kw_rule['force']]}. "
                        f"({kw_rule['note']})"
                    )
                    ep = kw_rule["force"]
                    break
                elif kw_rule["bump"] is not None:
                    bumped = max(1, ep - kw_rule["bump"])
                    if bumped < ep:
                        reasons.append(
                            f"Tier 4: keyword '{matched_kw}' detected "
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

SUBTYPE_CHOICES = [
    ("",               "— Optional —"),
    ("complete_outage","Complete Outage / Not Working At All"),
    ("no_boot",        "Not turning on / won't boot"),
    ("slow",           "Slow performance / intermittent"),
    ("display",        "Display / monitor issue"),
    ("peripheral",     "Peripheral not recognized"),
    ("app_crash",      "Application crash / error code"),
    ("no_login",       "Cannot log in / locked out"),
    ("no_internet",    "No internet / network access"),
    ("slow_conn",      "Slow connection"),
    ("pw_reset",       "Password reset needed"),
    ("new_user",       "New user / onboarding setup"),
    ("data_loss",      "Data loss / corruption concern"),
]

PRIORITY_CHOICES = [
    (4, "Low — Minor issue, no work stoppage"),
    (3, "Medium — Workaround exists, productivity affected"),
    (2, "High — Work is halted, team affected"),
    (1, "Critical — System down, department or city-wide"),
]
