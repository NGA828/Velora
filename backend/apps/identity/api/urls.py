from django.urls import path

from apps.identity.api.views import (
    ChangePasswordView,
    ClinicalStaffDirectoryView,
    CSRFCookieView,
    InvitationAcceptView,
    InvitationRevokeView,
    LoginView,
    LogoutView,
    MeView,
    MyAvatarView,
    SessionView,
    StaffDetailView,
    StaffInvitationListCreateView,
    StaffListView,
)

app_name = "identity"

urlpatterns = [
    path("auth/csrf/", CSRFCookieView.as_view(), name="csrf"),
    path("auth/session/", SessionView.as_view(), name="session"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/me/avatar/", MyAvatarView.as_view(), name="my-avatar"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/password/change/", ChangePasswordView.as_view(), name="change-password"),
    path(
        "auth/invitations/accept/",
        InvitationAcceptView.as_view(),
        name="accept-invitation",
    ),
    path("staff/", StaffListView.as_view(), name="staff-list"),
    path(
        "staff/clinical-directory/",
        ClinicalStaffDirectoryView.as_view(),
        name="clinical-staff-directory",
    ),
    path("staff/<uuid:pk>/", StaffDetailView.as_view(), name="staff-detail"),
    path(
        "staff/invitations/",
        StaffInvitationListCreateView.as_view(),
        name="staff-invitations",
    ),
    path(
        "staff/invitations/<uuid:invitation_id>/revoke/",
        InvitationRevokeView.as_view(),
        name="revoke-invitation",
    ),
]
