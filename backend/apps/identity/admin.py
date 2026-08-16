from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.identity.models import (
    Invitation,
    LoginEvent,
    PatientGuardProfile,
    StaffProfile,
    User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "get_full_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined", "updated_at")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identity", {"fields": ("first_name", "last_name", "phone", "role")}),
        (
            "Access",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "must_change_password",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Timestamps", {"fields": ("last_login", "date_joined", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_number", "user", "department", "employment_status")
    list_filter = ("employment_status", "department")
    search_fields = ("employee_number", "user__email", "user__first_name", "user__last_name")


@admin.register(PatientGuardProfile)
class PatientGuardProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_contact_method", "preferred_language")
    search_fields = ("user__email", "user__first_name", "user__last_name")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "intended_role",
        "invited_by",
        "expires_at",
        "accepted_at",
        "revoked_at",
    )
    list_filter = ("intended_role",)
    search_fields = ("email",)
    readonly_fields = ("token_hash", "accepted_at", "revoked_at", "created_at", "updated_at")


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "email_attempted", "outcome", "ip_address")
    list_filter = ("outcome",)
    search_fields = ("email_attempted",)
    readonly_fields = [field.name for field in LoginEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
