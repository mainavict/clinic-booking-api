import enum

class AppointmentStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"