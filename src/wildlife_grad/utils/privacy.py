"""Helpers for keeping personal contact details out of stored and published data."""

import re

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
REDACTED_EMAIL = "[email removed]"


def redact_emails(value):
    """Replace email addresses in a string; non-strings are returned unchanged."""
    if not isinstance(value, str):
        return value
    return EMAIL_PATTERN.sub(REDACTED_EMAIL, value)
