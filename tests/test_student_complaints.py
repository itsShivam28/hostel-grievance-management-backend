import pytest
from fastapi.testclient import TestClient

from app.models import Workman
from tests.conftest import StudentFactory, WardenFactory
from tests.helpers import assign, file_complaint


def test_new_complaint_starts_pending_in_students_hostel(
    client: TestClient, make_student: StudentFactory
) -> None:
    headers = make_student(hostel_name="Hostel A")

    complaint = file_complaint(
        client, headers, category="Water", description="Tap is leaking badly"
    )

    assert complaint["status"] == "PENDING"
    assert complaint["category"] == "Water"
    assert complaint["hostel_name"] == "HOSTEL A"
    assert complaint["is_urgent"] is False
    assert complaint["student_verified"] is False
    assert complaint["photo_url"] is None
    assert complaint["point_of_contact"] is None


def test_complaint_accepts_optional_photo_url(
    client: TestClient, make_student: StudentFactory
) -> None:
    headers = make_student()

    complaint = file_complaint(client, headers, photo_url="https://cdn.example.com/leak.jpg")

    assert complaint["photo_url"] == "https://cdn.example.com/leak.jpg"


@pytest.mark.parametrize(
    "overrides",
    [
        {"category": "Plumbing"},
        {"description": "hey"},
        {"photo_url": "not-a-url"},
        {"photo_url": "javascript:alert(1)"},
    ],
)
def test_invalid_complaints_are_rejected(
    client: TestClient, make_student: StudentFactory, overrides: dict[str, str]
) -> None:
    headers = make_student()
    payload = {"category": "Generic", "description": "Corridor light is broken"} | overrides

    response = client.post("/student/complaints", json=payload, headers=headers)

    assert response.status_code == 422


def test_client_cannot_override_status_or_urgency(
    client: TestClient, make_student: StudentFactory
) -> None:
    headers = make_student()

    complaint = file_complaint(
        client, headers, status="CLOSED", is_urgent=True, student_verified=True
    )

    assert complaint["status"] == "PENDING"
    assert complaint["is_urgent"] is False
    assert complaint["student_verified"] is False


def test_students_only_see_their_own_complaints(
    client: TestClient, make_student: StudentFactory
) -> None:
    alice = make_student("alice@iiitdmj.ac.in")
    bob = make_student("bob@iiitdmj.ac.in")
    file_complaint(client, alice, description="Alice's broken fan")
    file_complaint(client, bob, description="Bob's broken window")

    response = client.get("/student/complaints", headers=alice)

    assert [item["description"] for item in response.json()] == ["Alice's broken fan"]


def test_listing_is_newest_first_and_paginated(
    client: TestClient, make_student: StudentFactory
) -> None:
    headers = make_student()
    for number in range(3):
        file_complaint(client, headers, description=f"Issue number {number}")

    first_page = client.get("/student/complaints?limit=2", headers=headers).json()
    second_page = client.get("/student/complaints?limit=2&offset=2", headers=headers).json()

    assert [item["description"] for item in first_page] == ["Issue number 2", "Issue number 1"]
    assert [item["description"] for item in second_page] == ["Issue number 0"]


def test_point_of_contact_is_shown_only_while_work_is_in_progress(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]

    pending = client.get("/student/complaints", headers=student).json()[0]
    assert pending["point_of_contact"] is None

    assign(client, warden, complaint_id, workman.id)
    working = client.get("/student/complaints", headers=student).json()[0]
    assert working["status"] == "WORKING"
    assert working["point_of_contact"] == {"name": "Ramesh Kumar", "contact": "+91 98765 43210"}

    client.post(f"/student/complaints/{complaint_id}/verify", headers=student)
    resolved = client.get("/student/complaints", headers=student).json()[0]
    assert resolved["status"] == "RESOLVED"
    assert resolved["point_of_contact"] is None


def test_student_verification_resolves_complaint(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]
    assign(client, warden, complaint_id, workman.id)

    response = client.post(f"/student/complaints/{complaint_id}/verify", headers=student)

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"
    assert response.json()["student_verified"] is True


def test_cannot_verify_before_work_starts(client: TestClient, make_student: StudentFactory) -> None:
    student = make_student()
    complaint_id = file_complaint(client, student)["id"]

    response = client.post(f"/student/complaints/{complaint_id}/verify", headers=student)

    assert response.status_code == 409
    listed = client.get("/student/complaints", headers=student).json()[0]
    assert listed["status"] == "PENDING"
    assert listed["student_verified"] is False


def test_cannot_verify_twice(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]
    assign(client, warden, complaint_id, workman.id)
    client.post(f"/student/complaints/{complaint_id}/verify", headers=student)

    response = client.post(f"/student/complaints/{complaint_id}/verify", headers=student)

    assert response.status_code == 409


def test_student_cannot_verify_someone_elses_complaint(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    owner, intruder, warden = (
        make_student("owner@iiitdmj.ac.in"),
        make_student("intruder@iiitdmj.ac.in"),
        make_warden(),
    )
    complaint_id = file_complaint(client, owner)["id"]
    assign(client, warden, complaint_id, workman.id)

    response = client.post(f"/student/complaints/{complaint_id}/verify", headers=intruder)

    assert response.status_code == 404
    assert client.get("/student/complaints", headers=owner).json()[0]["status"] == "WORKING"


def test_verifying_unknown_complaint_returns_404(
    client: TestClient, make_student: StudentFactory
) -> None:
    response = client.post("/student/complaints/424242/verify", headers=make_student())

    assert response.status_code == 404
