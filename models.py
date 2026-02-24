from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Connection(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="connections",
    )
    connected_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="connected_to",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "connected_user")
        indexes = [
            models.Index(fields=["user", "connected_user"], name="net_conn_user_idx"),
        ]

    def clean(self):
        if self.user_id == self.connected_user_id:
            raise ValidationError("Users cannot connect to themselves.")

    def __str__(self) -> str:
        return f"{self.user} -> {self.connected_user}"


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")
        indexes = [
            models.Index(fields=["follower", "following"], name="net_follow_pair_idx"),
        ]

    def clean(self):
        if self.follower_id == self.following_id:
            raise ValidationError("Users cannot follow themselves.")

    def __str__(self) -> str:
        return f"{self.follower} follows {self.following}"


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_invitations",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["from_user", "to_user", "status"], name="net_inv_status_idx"),
        ]

    def clean(self):
        if self.from_user_id == self.to_user_id:
            raise ValidationError("Users cannot invite themselves.")

    def mark_responded(self, status: str):
        self.status = status
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def __str__(self) -> str:
        return f"{self.from_user} -> {self.to_user} ({self.status})"
