from typing import Any

def get_site_setting(key: str, fallback: Any = None) -> Any:
    """
    Retrieve a site setting value by key with a fallback if not set.
    Returns string values; callers can cast as needed.
    """
    from .models import SiteSetting
    try:
        s = SiteSetting.objects.filter(key=key).first()
        if s and s.value is not None and s.value != "":
            return s.value
    except Exception:
        # On any DB error return fallback
        pass
    return fallback
