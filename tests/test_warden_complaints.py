from fastapi.testclient import TestClient

from app.models import Workman
from tests.conftest import StudentFactory, WardenFactory
from tests.helpers import assign, file_complaint


def test_warden_sees_only_complaints_from_their_hostel(
    client: TestClient, make_student: StudentFactory, make_warden: WardenFactory
) -> None:
    warden = make_warden(hostel_name="Hostel A")
    in_hostel = make_student("a@iiitdmj.ac.in", "Hostel A")
    elsewhere = make_student("b@iiitdmj.ac.in", "Hostel B")
    file_complaint(client, in_hostel, description="Visible to warden A")
    file_complaint(client, elsewhere, description="Hidden from warden A")

    response = client.get("/warden/complaints", headers=warden)

    assert response.status_code == 200
    assert [item["description"] for item in response.json()] == ["Visible to warden A"]


def test_hostel_matching_ignores_case_and_spacing(
    client: TestClient, make_student: StudentFactory, make_warden: WardenFactory
) -> None:
    warden = make_warden(hostel_name="Aryabhatta  Hostel")
    student = make_student("a@iiitdmj.ac.in", "  aryabhatta hostel ")
    file_complaint(client, student)

    assert len(client.get("/warden/complaints", headers=warden).json()) == 1


def test_warden_listing_includes_student_and_workman_details(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]
    assign(client, warden, complaint_id, workman.id)

    item = client.get("/warden/complaints", headers=warden).json()[0]

    assert item["student_id"] > 0
    assert item["assigned_workman"] == {
        "id": workman.id,
        "name": "Ramesh Kumar",
        "contact": "+91 98765 43210",
        "category": "Electricity",
    }


def test_warden_can_filter_by_status(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    first = file_complaint(client, student, description="First complaint")["id"]
    file_complaint(client, student, description="Second complaint")
    assign(client, warden, first, workman.id)

    pending = client.get("/warden/complaints?status=PENDING", headers=warden).json()
    working = client.get("/warden/complaints?status=WORKING", headers=warden).json()

    assert [item["description"] for item in pending] == ["Second complaint"]
    assert [item["description"] for item in working] == ["First complaint"]
    assert client.get("/warden/complaints?status=BOGUS", headers=warden).status_code == 422


def test_assigning_workman_moves_complaint_to_working(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]

    result = assign(client, warden, complaint_id, workman.id)

    assert result["status"] == "WORKING"
    assert result["assigned_workman"]["id"] == workman.id


def test_only_pending_complaints_can_be_assigned(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]
    assign(client, warden, complaint_id, workman.id)

    response = client.post(
        f"/warden/complaints/{complaint_id}/assign",
        json={"workman_id": workman.id},
        headers=warden,
    )

    assert response.status_code == 409


def test_assigning_unknown_workman_returns_404_and_keeps_complaint_pending(
    client: TestClient, make_student: StudentFactory, make_warden: WardenFactory
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]

    response = client.post(
        f"/warden/complaints/{complaint_id}/assign", json={"workman_id": 9999}, headers=warden
    )

    assert response.status_code == 404
    assert client.get("/student/complaints", headers=student).json()[0]["status"] == "PENDING"


def test_warden_cannot_touch_other_hostels_complaints(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    other_warden = make_warden("other@iiitdmj.ac.in", "Hostel B")
    student = make_student(hostel_name="Hostel A")
    complaint_id = file_complaint(client, student)["id"]

    assign_response = client.post(
        f"/warden/complaints/{complaint_id}/assign",
        json={"workman_id": workman.id},
        headers=other_warden,
    )
    close_response = client.post(f"/warden/complaints/{complaint_id}/close", headers=other_warden)

    assert assign_response.status_code == 404
    assert close_response.status_code == 404


def test_complaint_cannot_be_closed_before_student_verifies(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]

    pending_close = client.post(f"/warden/complaints/{complaint_id}/close", headers=warden)
    assign(client, warden, complaint_id, workman.id)
    working_close = client.post(f"/warden/complaints/{complaint_id}/close", headers=warden)

    assert pending_close.status_code == 409
    assert working_close.status_code == 409
    assert client.get("/student/complaints", headers=student).json()[0]["status"] == "WORKING"


def test_full_lifecycle_ends_with_warden_closing_verified_complaint(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]
    assign(client, warden, complaint_id, workman.id)
    client.post(f"/student/complaints/{complaint_id}/verify", headers=student)

    response = client.post(f"/warden/complaints/{complaint_id}/close", headers=warden)

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"
    assert response.json()["student_verified"] is True


def test_closed_complaint_cannot_be_closed_again(
    client: TestClient,
    make_student: StudentFactory,
    make_warden: WardenFactory,
    workman: Workman,
) -> None:
    student, warden = make_student(), make_warden()
    complaint_id = file_complaint(client, student)["id"]
    assign(client, warden, complaint_id, workman.id)
    client.post(f"/student/complaints/{complaint_id}/verify", headers=student)
    client.post(f"/warden/complaints/{complaint_id}/close", headers=warden)

    response = client.post(f"/warden/complaints/{complaint_id}/close", headers=warden)

    assert response.status_code == 409


def test_warden_can_register_and_list_workmen(
    client: TestClient, make_warden: WardenFactory
) -> None:
    warden = make_warden()

    created = client.post(
        "/warden/workmen",
        json={"name": "Suresh Patil", "contact": "9876543210", "category": "Water"},
        headers=warden,
    )
    listed = client.get("/warden/workmen", headers=warden)

    assert created.status_code == 201
    assert created.json()["category"] == "Water"
    assert [item["name"] for item in listed.json()] == ["Suresh Patil"]


def test_workman_contact_must_look_like_a_phone_number(
    client: TestClient, make_warden: WardenFactory
) -> None:
    response = client.post(
        "/warden/workmen",
        json={"name": "Suresh Patil", "contact": "call me maybe", "category": "Water"},
        headers=make_warden(),
    )

    assert response.status_code == 422
