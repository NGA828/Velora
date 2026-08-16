from django.db.models import QuerySet

from apps.identity.models import StaffProfile, UserRole


def staff_visible_to(user) -> QuerySet[StaffProfile]:
    queryset = StaffProfile.objects.select_related("user", "department")
    if user.role == UserRole.ADMIN:
        return queryset
    if user.role == UserRole.HEAD_OF_SERVICE:
        return queryset.filter(user__role__in=[UserRole.DOCTOR, UserRole.NURSE])
    return queryset.none()
