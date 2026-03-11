"""Cookie normalization helpers shared by login and server code."""

from dataclasses import dataclass


COOKIE_ATTRIBUTE_KEYS = {
    "path",
    "domain",
    "expires",
    "max-age",
    "samesite",
    "priority",
    "partitioned",
}


@dataclass(frozen=True)
class NormalizedCookie:
    """Normalized cookie parsing result."""

    value: str
    invalid_parts: int
    has_session: bool


def normalize_cookie_string(raw: str) -> NormalizedCookie:
    """Normalize a raw Cookie string into request-ready `key=value` pairs only."""
    if not raw:
        return NormalizedCookie(value="", invalid_parts=0, has_session=False)

    cleaned = raw.replace("\n", "").replace("\r", "").strip()
    if not cleaned:
        return NormalizedCookie(value="", invalid_parts=0, has_session=False)

    cookie_map: dict[str, str] = {}
    invalid_parts = 0

    for part in cleaned.split(";"):
        segment = part.strip()
        if not segment:
            continue
        if "=" not in segment:
            invalid_parts += 1
            continue

        key, value = segment.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or any(ch.isspace() for ch in key):
            invalid_parts += 1
            continue
        if key.lower() in COOKIE_ATTRIBUTE_KEYS:
            invalid_parts += 1
            continue

        cookie_map[key] = value

    value = "; ".join(f"{key}={val}" for key, val in cookie_map.items())
    has_session = any(key in cookie_map for key in ("sessionid", "sessionid_ss"))
    return NormalizedCookie(
        value=value,
        invalid_parts=invalid_parts,
        has_session=has_session,
    )
