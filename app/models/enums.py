from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "STUDENT"
    WARDEN = "WARDEN"


class ComplaintCategory(StrEnum):
    ELECTRICITY = "Electricity"
    WATER = "Water"
    GENERIC = "Generic"


class ComplaintStatus(StrEnum):
    PENDING = "PENDING"
    WORKING = "WORKING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
