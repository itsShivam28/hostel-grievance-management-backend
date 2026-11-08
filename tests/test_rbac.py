import pytest
from fastapi.testclient import TestClient

from tests.conftest import StudentFactory, WardenFactory

STUDENT_ONLY = [
    ("post", "/student/complaints"),
    ("get", "/student/complaints"),
    ("post", "/student/complaints/1/verify"),
]

WARDEN_ONLY = [
    ("get", "/warden/complaints"),
    ("post", "/warden/complaints/1/assign"),
    ("post", "/warden/complaints/1/close"),
    ("get", "/warden/workmen"),
    ("post", "/warden/workmen"),
]


@pytest.mark.parametrize(("method", "path"), STUDENT_ONLY + WARDEN_ONLY)
def test_anonymous_requests_are_rejected(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), WARDEN_ONLY)
def test_students_cannot_use_warden_endpoints(
    client: TestClient, make_student: StudentFactory, method: str, path: str
) -> None:
    headers = make_student()

    assert client.request(method, path, headers=headers).status_code == 403


@pytest.mark.parametrize(("method", "path"), STUDENT_ONLY)
def test_wardens_cannot_use_student_endpoints(
    client: TestClient, make_warden: WardenFactory, method: str, path: str
) -> None:
    headers = make_warden()

    assert client.request(method, path, headers=headers).status_code == 403


def test_health_check_is_public(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
