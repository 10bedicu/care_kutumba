from care.utils.models.base import BaseModel
from django.conf import settings
from django.db import models


class KutumbaRequestLog(BaseModel):
    request_id = models.CharField(max_length=20)
    response_id = models.CharField(max_length=255, null=True, blank=True)
    rc_number = models.CharField(max_length=12)
    success = models.BooleanField()
    status_code = models.IntegerField()
    status_text = models.CharField(max_length=255)
    members = models.JSONField(default=list)
    member_count = models.PositiveIntegerField(default=0)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="kutumba_request_logs",
    )
    error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "care_kutumba_request_log"

    def __str__(self):
        return f"KutumbaRequestLog({self.request_id}, rc={self.rc_number}, success={self.success})"
