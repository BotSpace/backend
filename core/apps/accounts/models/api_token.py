import hashlib
import secrets

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _generate_token() -> str:
    return f"bsp_{secrets.token_hex(32)}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class PersonalAccessToken(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="api_tokens")
    name = models.CharField(_("Nomi"), max_length=100)
    token_hash = models.CharField(_("Token hash"), max_length=64, unique=True, db_index=True)
    prefix = models.CharField(_("Prefix"), max_length=12)
    last_used_at = models.DateTimeField(_("Oxirgi ishlatilgan"), null=True, blank=True)
    created_at = models.DateTimeField(_("Yaratilgan"), auto_now_add=True)

    class Meta:
        db_table = "personal_access_token"
        verbose_name = _("API token")
        verbose_name_plural = _("API tokenlar")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def create_token(cls, user, name: str = "API Token") -> tuple["PersonalAccessToken", str]:
        raw_token = _generate_token()
        obj = cls.objects.create(
            user=user,
            name=name,
            token_hash=_hash_token(raw_token),
            prefix=raw_token[:12],
        )
        return obj, raw_token

    @classmethod
    def verify(cls, raw_token: str) -> "PersonalAccessToken | None":
        h = _hash_token(raw_token)
        try:
            pat = cls.objects.select_related("user").get(token_hash=h)
            pat.last_used_at = timezone.now()
            pat.save(update_fields=["last_used_at"])
            return pat
        except cls.DoesNotExist:
            return None
