"""V1 pending deadline: an absolute 24 hours from the persisted binding."""
from datetime import datetime, timedelta, timezone


def utc_instant(value):
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def expires_at(binding_created_at):
    return utc_instant(binding_created_at) + timedelta(hours=24)
