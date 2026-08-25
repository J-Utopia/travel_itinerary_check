from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest

import 일정표웹 as web


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("105514210", None),
        (" 105-514-210 ", None),
    ],
)
def test_validate_group_id_accepts_normal_values(value: str, expected: str | None) -> None:
    assert web.validate_group_id(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", "단체번호를 입력해주세요."),
        ("12345", "단체번호는 숫자 6~12자리로 입력해주세요."),
        ("1234567890123", "단체번호는 숫자 6~12자리로 입력해주세요."),
    ],
)
def test_validate_group_id_rejects_failure_and_edge_values(value: str, expected: str) -> None:
    assert web.validate_group_id(value) == expected


def test_build_json_download_returns_valid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    data = {
        "title": "테스트 일정",
        "days": [{"day_no": 1, "schedule_items": []}],
    }
    fake_extractor = SimpleNamespace(
        build_extraction=lambda group_id: data | {"group_no": group_id},
        validate_extraction=lambda extracted: [],
    )

    monkeypatch.setattr(web, "load_extractor", lambda: fake_extractor)

    cached_build = cast(Any, web.build_json_download)
    uncached_build = cast(
        Callable[[str], tuple[str, bytes, dict[str, Any]]],
        cached_build.__wrapped__,
    )
    filename, payload, extracted = uncached_build("105514210")

    assert filename == "일정표_105514210.json"
    assert extracted["group_no"] == "105514210"
    assert json.loads(payload.decode("utf-8"))["title"] == "테스트 일정"


def test_extraction_error_message_explains_missing_modetour_header() -> None:
    message = web.extraction_error_message(
        RuntimeError("Failed to capture modewebapireqheader from ModeTour page.")
    )

    assert "MODETOUR_HEADER_CACHE_JSON" in message
    assert "MODETOUR_MODEWEBAPIREQHEADER" in message
