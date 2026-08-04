from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    seed_mat_code: str = os.getenv("MODETOUR_SEED_MAT_CODE", "MAT260119009")
    base_url: str = os.getenv("MODETOUR_B2C_BASE_URL", "https://b2c-api.modetour.com")
    request_timeout_seconds: int = int(os.getenv("MODETOUR_REQUEST_TIMEOUT_SECONDS", "30"))
    capture_timeout_ms: int = int(os.getenv("MODETOUR_CAPTURE_TIMEOUT_MS", "60000"))
    capture_wait_ms: int = int(os.getenv("MODETOUR_CAPTURE_WAIT_MS", "1200"))
    header_cache_path: Path = Path(os.getenv("MODETOUR_HEADER_CACHE_PATH", str(BASE_DIR / ".cache" / "modetour_headers.json")))
    header_cache_json: str = os.getenv("MODETOUR_HEADER_CACHE_JSON", "")
    modewebapireqheader: str = os.getenv("MODETOUR_MODEWEBAPIREQHEADER", "")
    x_platform: str = os.getenv("MODETOUR_X_PLATFORM", "WEB")
    x_salespartner: str = os.getenv("MODETOUR_X_SALESPARTNER", "false")
    x_username: str = os.getenv("MODETOUR_X_USERNAME", "")
    x_userid: str = os.getenv("MODETOUR_X_USERID", "0")
    x_userdepartment: str = os.getenv("MODETOUR_X_USERDEPARTMENT", "")
    user_agent: str = os.getenv("MODETOUR_USER_AGENT", "Mozilla/5.0")
    accept: str = os.getenv("MODETOUR_ACCEPT", "application/json, text/plain, */*")
    referer: str = os.getenv("MODETOUR_REFERER", "https://www.modetour.com/")


settings = Settings()
