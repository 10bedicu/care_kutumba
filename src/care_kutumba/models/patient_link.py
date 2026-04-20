from care.emr.models.patient import Patient
from care.utils.models.base import BaseModel
from django.conf import settings
from django.db import models


class KutumbaPatientLink(BaseModel):
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
    ]

    request_log = models.ForeignKey(
        "care_kutumba.KutumbaRequestLog",
        on_delete=models.PROTECT,
        related_name="patient_links",
    )
    selected_member_index = models.PositiveIntegerField()
    selected_member_data = models.JSONField(default=dict)
    rc_number = models.CharField(max_length=12)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="kutumba_links",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="kutumba_patient_links",
    )

    class Meta:
        db_table = "care_kutumba_patient_link"

    def __str__(self):
        return f"KutumbaPatientLink({self.action}, rc={self.rc_number}, patient={self.patient_id})"
