from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import PASSWORD, StudentFactory

VALID_REGISTRATION = {
    "email": "asha@iiitdmj.ac.in",
    "password": PASSWORD,
    "hostel_name": "Hostel A",
}


def test_register_creates_student_without_leaking_password(client: TestClient) -> None:
    response = client.post("/auth/register", json=VALID_REGISTRATION)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "asha@iiitdmj.ac.in"
    assert body["role"] == "STUDENT"
    assert body["hostel_name"] == "HOSTEL A"
    assert "password" not in body and "hashed_password" not in body


def test_register_normalises_email_case(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json=VALID_REGISTRATION | {"email": "Asha.K@IIITDMJ.AC.IN"}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "asha.k@iiitdmj.ac.in"


@pytest.mark.parametrize(
    "email",
    [
        "asha@gmail.com",
        "asha@iiitdmj.ac.in.evil.com",
        "asha@mail.iiitdmj.ac.in",
        "asha@iiitdmj.com",
        "not-an-email",
    ],
)
def test_register_rejects_non_institute_emails(client: TestClient, email: str) -> None:
    response = client.post("/auth/register", json=VALID_REGISTRATION | {"email": email})

    assert response.status_code == 422


def test_register_cannot_choose_warden_role(client: TestClient) -> None:
    response = client.post("/auth/register", json=VALID_REGISTRATION | {"role": "WARDEN"})

    assert response.status_code == 201
    assert response.json()["role"] == "STUDENT"


@pytest.mark.parametrize("password", ["short", "x" * 73, "é" * 40])
def test_register_rejects_unusable_passwords(client: TestClient, password: str) -> None:
    response = client.post("/auth/register", json=VALID_REGISTRATION | {"password": password})

    assert response.status_code == 422


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    client.post("/auth/register", json=VALID_REGISTRATION)

    response = client.post("/auth/register", json=VALID_REGISTRATION)

    assert response.status_code == 409


def test_login_returns_bearer_token_that_opens_me_endpoint(
    client: TestClient, make_student: StudentFactory
) -> None:
    headers = make_student("asha@iiitdmj.ac.in", "Hostel B")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "asha@iiitdmj.ac.in"
    assert response.json()["hostel_name"] == "HOSTEL B"


def test_login_is_case_insensitive_on_email(
    client: TestClient, make_student: StudentFactory
) -> None:
    make_student("asha@iiitdmj.ac.in")

    response = client.post(
        "/auth/login", data={"username": "ASHA@iiitdmj.ac.in", "password": PASSWORD}
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [("asha@iiitdmj.ac.in", "wrong-password"), ("ghost@iiitdmj.ac.in", PASSWORD)],
)
def test_login_failures_are_indistinguishable(
    client: TestClient, make_student: StudentFactory, email: str, password: str
) -> None:
    make_student("asha@iiitdmj.ac.in")

    response = client.post("/auth/login", data={"username": email, "password": password})

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_route_requires_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_garbage_token_is_rejected(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})

    assert response.status_code == 401


def test_expired_token_is_rejected(client: TestClient, make_student: StudentFactory) -> None:
    make_student()
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_token_signed_with_other_key_is_rejected(
    client: TestClient, make_student: StudentFactory
) -> None:
    make_student()
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "some-other-secret-key-that-is-long-enough-1234",
        algorithm="HS256",
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_token_for_unknown_user_is_rejected(client: TestClient) -> None:
    settings = get_settings()
    orphan = jwt.encode(
        {"sub": "9999", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {orphan}"})

    assert response.status_code == 401
