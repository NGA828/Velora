import pytest

from apps.identity.models import User, UserRole


@pytest.mark.django_db
def test_user_manager_normalizes_email_and_hashes_password():
    user = User.objects.create_user(
        email="Doctor@EXAMPLE.ORG",
        password="Foundation-passphrase-927!",
        first_name="Ada",
        last_name="Okafor",
        role=UserRole.DOCTOR,
    )

    assert user.email == "doctor@example.org"
    assert user.check_password("Foundation-passphrase-927!")
    assert user.password != "Foundation-passphrase-927!"


@pytest.mark.django_db
def test_superuser_is_always_an_admin():
    user = User.objects.create_superuser(
        email="admin@example.org",
        password="Foundation-passphrase-927!",
        first_name="System",
        last_name="Admin",
    )

    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
