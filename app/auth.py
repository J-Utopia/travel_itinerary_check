from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)

HEADER_KEYS = (
    "accept",
    "referer",
    "user-agent",
    "x-platform",
    "x-salespartner",
    "x-username",
    "x-userid",
    "x-userdepartment",
    "modewebapireqheader",
)
REQUIRED_HEADER_KEYS = (
    "accept",
    "referer",
    "user-agent",
    "x-platform",
    "x-salespartner",
    "modewebapireqheader",
)


class HeaderCaptureError(RuntimeError):
    """Raised when required ModeTour request headers cannot be created."""


def _ensure_playwright_subprocess_event_loop() -> None:
    if sys.platform != "win32":
        return

    proactor_policy = getattr(asyncio, "WindowsProactorEventLoopPolicy", None)
    selector_policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if proactor_policy is None or selector_policy is None:
        return

    if isinstance(asyncio.get_event_loop_policy(), selector_policy):
        asyncio.set_event_loop_policy(proactor_policy())


def _build_env_headers(settings: Settings) -> dict[str, str] | None:
    if not settings.modewebapireqheader:
        return None
    return {
        "accept": settings.accept,
        "referer": settings.referer,
        "user-agent": settings.user_agent,
        "x-platform": settings.x_platform,
        "x-salespartner": settings.x_salespartner,
        "x-username": settings.x_username,
        "x-userid": settings.x_userid,
        "x-userdepartment": settings.x_userdepartment,
        "modewebapireqheader": settings.modewebapireqheader,
    }


def _load_cached_headers(settings: Settings) -> dict[str, str] | None:
    if settings.header_cache_json.strip():
        try:
            data = json.loads(settings.header_cache_json)
        except Exception:
            data = None
        if isinstance(data, dict):
            if all(str(data.get(key, "")).strip() for key in REQUIRED_HEADER_KEYS):
                return {key: str(data.get(key, "")) for key in HEADER_KEYS}

    cache_path = settings.header_cache_path
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if any(not str(data.get(key, "")).strip() for key in REQUIRED_HEADER_KEYS):
        return None
    return {key: str(data.get(key, "")) for key in HEADER_KEYS}


def _save_cached_headers(settings: Settings, headers: dict[str, str]) -> None:
    cache_path = settings.header_cache_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(headers, ensure_ascii=False, indent=2), encoding="utf-8")


def _capture_headers_with_playwright(settings: Settings, force_refresh: bool) -> dict[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on local install
        raise HeaderCaptureError("Playwright is required to capture ModeTour headers.") from exc

    _ensure_playwright_subprocess_event_loop()

    captured: dict[str, str] = {}

    def on_request(req: Any) -> None:
        nonlocal captured
        if "/Package/GetProductMaster" in req.url and req.method.upper() == "POST":
            captured = dict(req.headers)

    page_url = f"https://www.modetour.com/product-common/{settings.seed_mat_code}?type=single"
    logger.info("Capturing ModeTour headers from %s force_refresh=%s", page_url, force_refresh)
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" not in message and "Please run the following command" not in message:
                raise
            logger.warning("Playwright Chromium is missing; installing browser runtime once.")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                cwd=settings.base_dir,
                check=True,
            )
            browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("request", on_request)
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=settings.capture_timeout_ms)
        except Exception:
            logger.info("Navigation timed out while capturing headers; continuing if request data was captured.")
        page.wait_for_timeout(settings.capture_wait_ms)
        browser.close()

    modeweb = captured.get("modewebapireqheader", "")
    if not modeweb:
        raise HeaderCaptureError("Failed to capture modewebapireqheader from ModeTour page.")
    headers = {
        "accept": captured.get("accept", settings.accept),
        "referer": settings.referer,
        "user-agent": captured.get("user-agent", settings.user_agent),
        "x-platform": captured.get("x-platform", settings.x_platform),
        "x-salespartner": captured.get("x-salespartner", settings.x_salespartner),
        "x-username": captured.get("x-username", settings.x_username),
        "x-userid": captured.get("x-userid", settings.x_userid),
        "x-userdepartment": captured.get("x-userdepartment", settings.x_userdepartment),
        "modewebapireqheader": modeweb,
    }
    _save_cached_headers(settings, headers)
    return headers


def _capture_headers_in_subprocess(settings: Settings, force_refresh: bool) -> dict[str, str]:
    command = [sys.executable, "-m", "app.auth", "--capture-headers"]
    if force_refresh:
        command.append("--force-refresh")

    env = os.environ.copy()
    env["MODETOUR_HEADER_CAPTURE_CHILD"] = "1"
    timeout_seconds = max(30, int((settings.capture_timeout_ms + settings.capture_wait_ms) / 1000) + 30)
    completed = subprocess.run(
        command,
        cwd=settings.base_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise HeaderCaptureError(f"Failed to capture ModeTour headers in a subprocess. {detail}") from None
    try:
        data = json.loads(completed.stdout)
    except Exception as exc:
        raise HeaderCaptureError("Header capture subprocess returned invalid JSON.") from exc
    if not isinstance(data, dict) or any(not str(data.get(key, "")).strip() for key in REQUIRED_HEADER_KEYS):
        raise HeaderCaptureError("Header capture subprocess returned incomplete headers.")
    return {key: str(data.get(key, "")) for key in HEADER_KEYS}


def capture_base_headers(settings: Settings, force_refresh: bool = False) -> dict[str, str]:
    if not force_refresh:
        env_headers = _build_env_headers(settings)
        if env_headers is not None:
            logger.info("Using ModeTour headers from environment variables.")
            return env_headers

        cached_headers = _load_cached_headers(settings)
        if cached_headers is not None:
            logger.info("Using cached ModeTour headers from %s", settings.header_cache_path)
            return cached_headers

    try:
        return _capture_headers_with_playwright(settings, force_refresh)
    except (NotImplementedError, RuntimeError) as exc:
        if os.getenv("MODETOUR_HEADER_CAPTURE_CHILD") == "1":
            raise HeaderCaptureError("Playwright cannot run in this Python event loop policy.") from exc
        logger.warning("Direct Playwright header capture failed; retrying in a subprocess.", exc_info=True)
        return _capture_headers_in_subprocess(settings, force_refresh)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-headers", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args(argv)
    if not args.capture_headers:
        return 0

    from .config import settings

    headers = capture_base_headers(settings, force_refresh=args.force_refresh)
    json.dump(headers, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
