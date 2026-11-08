import os

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-comfortably-over-32-chars"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["CREATE_TABLES_ON_STARTUP"] = "false"
os.environ["URGENCY_JOB_ENABLED"] = "false"

from collections.abc import Callable, Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.crud import user as user_crud  # noqa: E402
from app.crud import workman as workman_crud  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ComplaintCategory, User, Workman  # noqa: E402
from app.schemas.user import WardenCreation  # noqa: E402
from app.schemas.workman import WorkmanCreate  # noqa: E402
from app.services import auth as auth_service  # noqa: E402

PASSWORD = "correct-horse-battery"

AuthHeaders = dict[str, str]
StudentFactory = Callable[..., AuthHeaders]
WardenFactory = Callable[..., AuthHeaders]


def _build_engine() -> Engine:
    if TEST_DATABASE_URL.startswith("sqlite"):
        return create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    test_engine = _build_engine()
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str, password: str = PASSWORD) -> AuthHeaders:
    response = client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def make_student(client: TestClient) -> StudentFactory:
    def factory(email: str = "student@iiitdmj.ac.in", hostel_name: str = "Hostel A") -> AuthHeaders:
        response = client.post(
            "/auth/register",
            json={"email": email, "password": PASSWORD, "hostel_name": hostel_name},
        )
        assert response.status_code == 201, response.text
        return _login(client, email)

    return factory


@pytest.fixture
def make_warden(client: TestClient, db: Session) -> WardenFactory:
    def factory(email: str = "warden@iiitdmj.ac.in", hostel_name: str = "Hostel A") -> AuthHeaders:
        auth_service.create_warden(
            db, WardenCreation(email=email, password=PASSWORD, hostel_name=hostel_name)
        )
        return _login(client, email)

    return factory


@pytest.fixture
def workman(db: Session) -> Workman:
    payload = WorkmanCreate(
        name="Ramesh Kumar",
        contact="+91 98765 43210",
        category=ComplaintCategory.ELECTRICITY,
    )
    return workman_crud.create(db, payload)


@pytest.fixture
def student_user(db: Session, make_student: StudentFactory) -> User:
    make_student("seed@iiitdmj.ac.in", "Hostel A")
    user = user_crud.get_by_email(db, "seed@iiitdmj.ac.in")
    assert user is not None
    return user
