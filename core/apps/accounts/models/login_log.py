from django.db import models
from django.conf import settings


class LoginLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    method = models.CharField(max_length=20)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} via {self.method} at {self.created_at}"
