# type: ignore
"""Resurs monitoringi uchun davriy snapshot modeli.

Prometheus CPU/RAM/network tarixini o'zi saqlaydi (range query bilan olamiz), lekin
disk hajmi (yuklab olingan fayllar + CMS hujjatlari) Prometheus'da yo'q — uni biz
DB/Mongo'dan hisoblaymiz. Tarix chizish uchun celery beat har soatda har loyihaning
disk hajmini shu jadvalga yozadi.
"""

from django.db import models


class ProjectResourceSnapshot(models.Model):
    project = models.ForeignKey(
        "api.ProjectModel",
        on_delete=models.CASCADE,
        related_name="resource_snapshots",
    )
    disk_bytes = models.BigIntegerField(default=0)
    disk_files_bytes = models.BigIntegerField(default=0)
    disk_cms_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["project", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"snapshot project={self.project_id} disk={self.disk_bytes} @ {self.created_at}"
