"""Non-destructive navigation between independent local learning profiles."""

from urllib.parse import urlencode
from uuid import uuid4


def new_learning_profile_url(is_zh: bool, current_user_id: str) -> str:
    """Open a fresh, addressable draft without changing any saved profile.

    Keep the generated ID in the URL so refreshing the form does not create
    another draft. Nothing is written until the learner submits their goals.
    """
    return "?" + urlencode({
        "ui_language": "zh" if is_zh else "en",
        "user_id": f"learner-{uuid4().hex[:12]}",
        "new_profile": "1",
        "return_profile": current_user_id,
        "return_language": "zh" if is_zh else "en",
    }) + "#learning-brief"


def learning_profile_url(is_zh: bool, user_id: str) -> str:
    return "?" + urlencode({
        "ui_language": "zh" if is_zh else "en",
        "user_id": user_id,
    }) + "#reading-journey"
