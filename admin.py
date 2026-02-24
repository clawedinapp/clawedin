from django.contrib import admin

from .models import Connection, Follow, Invitation


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ("user", "connected_user", "created_at")
    search_fields = ("user__username", "connected_user__username")
    list_filter = ("created_at",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")
    list_filter = ("created_at",)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at", "responded_at")
    search_fields = ("from_user__username", "to_user__username")
    list_filter = ("status", "created_at")
