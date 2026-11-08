import argparse
import getpass
import sys

from pydantic import ValidationError

from app.core.exceptions import AppError
from app.database import Base, SessionLocal, engine
from app.schemas.user import WardenCreation
from app.services import auth as auth_service


def create_warden(email: str, hostel_name: str) -> int:
    password = getpass.getpass("Password: ")
    try:
        payload = WardenCreation(email=email, password=password, hostel_name=hostel_name)
    except ValidationError as exc:
        for error in exc.errors():
            print(f"{error['loc'][0]}: {error['msg']}", file=sys.stderr)
        return 1

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        try:
            warden = auth_service.create_warden(db, payload)
        except AppError as exc:
            print(exc.detail, file=sys.stderr)
            return 1
    print(f"Created warden {warden.email} for hostel {warden.hostel_name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    warden_parser = commands.add_parser("create-warden", help="Create a warden account")
    warden_parser.add_argument("--email", required=True)
    warden_parser.add_argument("--hostel", required=True)

    args = parser.parse_args()
    return create_warden(args.email, args.hostel)


if __name__ == "__main__":
    raise SystemExit(main())
