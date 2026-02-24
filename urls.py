from django.urls import path

from . import views

app_name = "network"

urlpatterns = [
    path("network/", views.network_home, name="home"),
    path("network/search/", views.user_search, name="search"),
    path("network/connections/", views.connections_list, name="connections"),
    path("network/followers/", views.followers_list, name="followers"),
    path("network/mutuals/", views.mutuals_list, name="mutuals"),
    path("network/invitations/", views.invitations_list, name="invitations"),
    path("network/invitations/send/<int:user_id>/", views.send_invitation, name="invitation_send"),
    path("network/invitations/<int:invitation_id>/accept/", views.accept_invitation, name="invitation_accept"),
    path("network/invitations/<int:invitation_id>/decline/", views.decline_invitation, name="invitation_decline"),
    path("network/invitations/<int:invitation_id>/withdraw/", views.withdraw_invitation, name="invitation_withdraw"),
    path("network/connections/<int:user_id>/remove/", views.remove_connection, name="connection_remove"),
    path("network/follow/<int:user_id>/", views.toggle_follow, name="follow_toggle"),
]
