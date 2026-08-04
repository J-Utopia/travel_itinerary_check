from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _has_streamlit_secrets_file() -> bool:
    return any(
        path.exists()
        for path in (
            BASE_DIR / ".streamlit" / "secrets.toml",
            Path.home() / ".streamlit" / "secrets.toml",
        )
    )


def _setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None:
        return value
    if not _has_streamlit_secrets_file():
        return default
    try:
        import streamlit as st

        secret = st.secrets.get(name)
    except Exception:
        return default
    return str(secret) if secret is not None else default


@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    seed_mat_code: str = _setting("MODETOUR_SEED_MAT_CODE", "MAT260119009")
    base_url: str = _setting("MODETOUR_B2C_BASE_URL", "https://b2c-api.modetour.com")
    request_timeout_seconds: int = int(_setting("MODETOUR_REQUEST_TIMEOUT_SECONDS", "30"))
    capture_timeout_ms: int = int(_setting("MODETOUR_CAPTURE_TIMEOUT_MS", "60000"))
    capture_wait_ms: int = int(_setting("MODETOUR_CAPTURE_WAIT_MS", "1200"))
    header_cache_path: Path = Path(_setting("MODETOUR_HEADER_CACHE_PATH", str(BASE_DIR / ".cache" / "modetour_headers.json")))
    header_cache_json: str = _setting("MODETOUR_HEADER_CACHE_JSON")
    modewebapireqheader: str = _setting("MODETOUR_MODEWEBAPIREQHEADER")
    x_platform: str = _setting("MODETOUR_X_PLATFORM", "ModeEcommerce")
    x_salespartner: str = _setting("MODETOUR_X_SALESPARTNER", "2")
    x_username: str = _setting("MODETOUR_X_USERNAME")
    x_userid: str = _setting("MODETOUR_X_USERID")
    x_userdepartment: str = _setting("MODETOUR_X_USERDEPARTMENT", "ModeEcommerce")
    user_agent: str = _setting("MODETOUR_USER_AGENT", "Mozilla/5.0")
    accept: str = _setting("MODETOUR_ACCEPT", "application/json, text/plain, */*")
    referer: str = _setting("MODETOUR_REFERER", "https://www.modetour.com/")


settings = Settings()
