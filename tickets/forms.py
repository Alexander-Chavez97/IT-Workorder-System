"""
tickets/forms.py
================
Django form for ticket submission.
Priority is determined automatically by the routing engine.
The WHEN and WHY fields of the 5 W's are required.
Input sanitization via strip_tags prevents stored XSS.
"""

from django import forms
from django.utils.html import strip_tags

from .routing import (
    DEPARTMENT_CHOICES,
    CATEGORY_CHOICES,
    SUBTYPE_CHOICES,
    ISSUE_TYPE_CHOICES,
)
from .models import Ticket


class TicketSubmitForm(forms.ModelForm):

    # ── Standard dropdowns ───────────────────────────────────────────────
    department = forms.ChoiceField(
        choices=[("", "— Select your department —")] + list(DEPARTMENT_CHOICES),
        widget=forms.Select(attrs={"id": "f_dept"}),
    )
    category = forms.ChoiceField(
        choices=[("", "— Select a category —")] + list(CATEGORY_CHOICES),
        widget=forms.Select(attrs={"id": "f_cat", "onchange": "onCategoryChange()"}),
    )
    subtype = forms.ChoiceField(
        choices=SUBTYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"id": "f_sub", "onchange": "onSubtypeChange()"}),
    )
    issue_type = forms.ChoiceField(
        choices=ISSUE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"id": "f_issue"}),
    )

    # ── 5 W's — WHEN and WHY are required ───────────────────────────────
    when_started = forms.CharField(
        label="When did this start?",
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. This morning around 9am, Since last Friday, Just now",
            "id": "f_when",
        }),
    )
    business_impact = forms.CharField(
        label="What work is blocked / why is this urgent?",
        required=True,
        widget=forms.Textarea(attrs={
            "placeholder": "e.g. Cannot process payroll, patients are waiting, cannot access dispatch system...",
            "id": "f_impact",
            "rows": 2,
        }),
    )
    affected_users = forms.CharField(
        label="Who else is affected? (optional)",
        required=False,
        widget=forms.Textarea(attrs={
            "placeholder": "e.g. Entire Finance dept, 3 employees on 2nd floor...",
            "id": "f_affected",
            "rows": 2,
        }),
    )

    class Meta:
        model = Ticket
        fields = [
            "name", "employee_id", "department", "email",
            "category", "subtype", "issue_type",
            "title", "description",
            "asset_tag", "location", "phone_ext",
            "affected_users", "when_started", "business_impact",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "e.g. Maria Gonzalez",
                "id": "f_name",
            }),
            "employee_id": forms.TextInput(attrs={
                "placeholder": "e.g. LRD-4821",
                "id": "f_empid",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "name@laredotx.gov",
                "id": "f_email",
            }),
            "title": forms.TextInput(attrs={
                "placeholder": "One-line summary of the issue",
                "id": "f_title",
                "maxlength": "120",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "What happened, when it started, any error messages, steps already tried...",
                "id": "f_desc",
                "rows": 4,
            }),
            "asset_tag": forms.TextInput(attrs={
                "placeholder": "e.g. LRD-PC-0042",
                "id": "f_asset",
            }),
            "location": forms.TextInput(attrs={
                "placeholder": "e.g. City Hall, Rm 204",
                "id": "f_loc",
            }),
            "phone_ext": forms.TextInput(attrs={
                "placeholder": "e.g. x3412",
                "id": "f_ext",
            }),
        }

    # ── Input sanitization ───────────────────────────────────────────────
    # Strip HTML tags from free-text fields before saving to the database.

    def _strip(self, field):
        return strip_tags(self.cleaned_data.get(field, "") or "")

    def clean_title(self):           return self._strip("title")
    def clean_description(self):     return self._strip("description")
    def clean_when_started(self):    return self._strip("when_started")
    def clean_business_impact(self): return self._strip("business_impact")
    def clean_affected_users(self):  return self._strip("affected_users")
    def clean_location(self):        return self._strip("location")
    def clean_asset_tag(self):       return self._strip("asset_tag")