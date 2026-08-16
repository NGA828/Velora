from apps.identity.models import StaffProfile, User, UserRole

DEFAULT_PASSWORD = "Foundation-passphrase-927!"


def create_user(*, role=UserRole.DOCTOR, email=None, password=DEFAULT_PASSWORD, **kwargs):
    email = email or f"{role.lower()}@example.org"
    return User.objects.create_user(
        email=email,
        password=password,
        first_name=kwargs.pop("first_name", "Test"),
        last_name=kwargs.pop("last_name", "User"),
        role=role,
        must_change_password=kwargs.pop("must_change_password", False),
        **kwargs,
    )


def create_staff(*, role=UserRole.DOCTOR, email=None, employee_number=None, **kwargs):
    user = create_user(role=role, email=email, **kwargs)
    profile = StaffProfile.objects.create(
        user=user,
        employee_number=employee_number or f"EMP-{str(user.id)[:8]}",
    )
    return user, profile
