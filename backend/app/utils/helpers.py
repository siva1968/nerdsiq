"""Helper utilities."""

import secrets
import string


def generate_session_id() -> str:
    """Generate a unique session ID."""
    chars = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(12))
    return f"sess_{random_part}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
