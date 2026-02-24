from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Connection, Follow, Invitation


def _redirect_back(request, fallback_name="network:home"):
    return redirect(request.META.get("HTTP_REFERER") or reverse(fallback_name))


def _create_connection(user, other):
    if user == other:
        return
    Connection.objects.get_or_create(user=user, connected_user=other)
    Connection.objects.get_or_create(user=other, connected_user=user)


def _remove_connection(user, other):
    Connection.objects.filter(user=user, connected_user=other).delete()
    Connection.objects.filter(user=other, connected_user=user).delete()


@login_required
def network_home(request):
    user = request.user
    context = {
        "connections_count": Connection.objects.filter(user=user).count(),
        "followers_count": Follow.objects.filter(following=user).count(),
        "following_count": Follow.objects.filter(follower=user).count(),
        "incoming_invites_count": Invitation.objects.filter(
            to_user=user,
            status=Invitation.Status.PENDING,
        ).count(),
        "outgoing_invites_count": Invitation.objects.filter(
            from_user=user,
            status=Invitation.Status.PENDING,
        ).count(),
    }
    return render(request, "network/network_home.html", context)


@login_required
def user_search(request):
    query = request.GET.get("q", "").strip()
    User = get_user_model()

    results = User.objects.exclude(id=request.user.id)
    if query:
        results = results.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(display_name__icontains=query)
        )
    else:
        results = results.none()

    results = list(results.order_by("username")[:50])
    result_ids = [user.id for user in results]

    connected_ids = set(
        Connection.objects.filter(user=request.user, connected_user_id__in=result_ids)
        .values_list("connected_user_id", flat=True)
    )
    outgoing_invites = Invitation.objects.filter(
        from_user=request.user,
        to_user_id__in=result_ids,
        status=Invitation.Status.PENDING,
    )
    outgoing_ids = set(outgoing_invites.values_list("to_user_id", flat=True))

    incoming_invites = Invitation.objects.filter(
        from_user_id__in=result_ids,
        to_user=request.user,
        status=Invitation.Status.PENDING,
    )
    incoming_by_user_id = {invite.from_user_id: invite for invite in incoming_invites}

    following_ids = set(
        Follow.objects.filter(follower=request.user, following_id__in=result_ids)
        .values_list("following_id", flat=True)
    )
    follower_ids = set(
        Follow.objects.filter(following=request.user, follower_id__in=result_ids)
        .values_list("follower_id", flat=True)
    )

    for user in results:
        user.is_connected = user.id in connected_ids
        user.outgoing_invite = user.id in outgoing_ids
        user.incoming_invite = incoming_by_user_id.get(user.id)
        user.is_following = user.id in following_ids
        user.is_follower = user.id in follower_ids

    context = {
        "query": query,
        "results": results,
    }
    return render(request, "network/user_search.html", context)


@login_required
def connections_list(request):
    connections = (
        Connection.objects.filter(user=request.user)
        .select_related("connected_user")
        .order_by("connected_user__username")
    )
    return render(request, "network/connections_list.html", {"connections": connections})


@login_required
def followers_list(request):
    followers = list(
        Follow.objects.filter(following=request.user)
        .select_related("follower")
        .order_by("follower__username")
    )
    following = list(
        Follow.objects.filter(follower=request.user)
        .select_related("following")
        .order_by("following__username")
    )
    following_ids = {follow.following_id for follow in following}
    for follow in followers:
        follow.is_followed_back = follow.follower_id in following_ids
    return render(
        request,
        "network/followers_list.html",
        {"followers": followers, "following": following},
    )


@login_required
def invitations_list(request):
    incoming = (
        Invitation.objects.filter(
            to_user=request.user,
            status=Invitation.Status.PENDING,
        )
        .select_related("from_user")
        .order_by("-created_at")
    )
    outgoing = (
        Invitation.objects.filter(
            from_user=request.user,
            status=Invitation.Status.PENDING,
        )
        .select_related("to_user")
        .order_by("-created_at")
    )
    return render(
        request,
        "network/invitations_list.html",
        {"incoming": incoming, "outgoing": outgoing},
    )


@login_required
def mutuals_list(request):
    User = get_user_model()
    connections = (
        Connection.objects.filter(user=request.user)
        .select_related("connected_user")
        .order_by("connected_user__username")
    )
    selected_user = None
    mutuals = []
    selected_id = request.GET.get("user_id")

    if selected_id:
        selected_user = get_object_or_404(User, id=selected_id)
        if selected_user != request.user:
            my_ids = set(connections.values_list("connected_user_id", flat=True))
            other_ids = set(
                Connection.objects.filter(user=selected_user)
                .exclude(connected_user=request.user)
                .values_list("connected_user_id", flat=True)
            )
            mutual_ids = my_ids & other_ids
            mutuals = User.objects.filter(id__in=mutual_ids).order_by("username")

    context = {
        "connections": connections,
        "selected_user": selected_user,
        "mutuals": mutuals,
    }
    return render(request, "network/mutuals_list.html", context)


@require_POST
@login_required
def send_invitation(request, user_id):
    User = get_user_model()
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        return _redirect_back(request, "network:search")

    if Connection.objects.filter(user=request.user, connected_user=target).exists():
        return _redirect_back(request, "network:search")

    incoming = Invitation.objects.filter(
        from_user=target,
        to_user=request.user,
        status=Invitation.Status.PENDING,
    ).first()
    if incoming:
        _create_connection(request.user, target)
        incoming.mark_responded(Invitation.Status.ACCEPTED)
        return _redirect_back(request, "network:search")

    if Invitation.objects.filter(
        from_user=request.user,
        to_user=target,
        status=Invitation.Status.PENDING,
    ).exists():
        return _redirect_back(request, "network:search")

    Invitation.objects.create(from_user=request.user, to_user=target)
    return _redirect_back(request, "network:search")


@require_POST
@login_required
def accept_invitation(request, invitation_id):
    invitation = get_object_or_404(
        Invitation,
        id=invitation_id,
        to_user=request.user,
        status=Invitation.Status.PENDING,
    )
    _create_connection(request.user, invitation.from_user)
    invitation.mark_responded(Invitation.Status.ACCEPTED)
    return _redirect_back(request, "network:invitations")


@require_POST
@login_required
def decline_invitation(request, invitation_id):
    invitation = get_object_or_404(
        Invitation,
        id=invitation_id,
        to_user=request.user,
        status=Invitation.Status.PENDING,
    )
    invitation.mark_responded(Invitation.Status.DECLINED)
    return _redirect_back(request, "network:invitations")


@require_POST
@login_required
def withdraw_invitation(request, invitation_id):
    invitation = get_object_or_404(
        Invitation,
        id=invitation_id,
        from_user=request.user,
        status=Invitation.Status.PENDING,
    )
    invitation.mark_responded(Invitation.Status.WITHDRAWN)
    return _redirect_back(request, "network:invitations")


@require_POST
@login_required
def remove_connection(request, user_id):
    User = get_user_model()
    target = get_object_or_404(User, id=user_id)
    _remove_connection(request.user, target)
    return _redirect_back(request, "network:connections")


@require_POST
@login_required
def toggle_follow(request, user_id):
    User = get_user_model()
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        return _redirect_back(request, "network:followers")

    existing = Follow.objects.filter(follower=request.user, following=target)
    if existing.exists():
        existing.delete()
    else:
        Follow.objects.create(follower=request.user, following=target)
    return _redirect_back(request, "network:followers")
