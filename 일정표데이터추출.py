from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.client import ModeTourApiClient  # noqa: E402
from app.config import settings  # noqa: E402
from app.normalizer import normalize_product  # noqa: E402

logger = logging.getLogger(__name__)


HARDCODED_GROUP_IDS: list[str] = [
    # 여기에 단체번호를 직접 넣으면 명령줄 인자 없이 실행할 수 있습니다.
    "105514210","110660263","103142823","105004292","104358660","100006820","101613285"
]


STATUS_LABELS = {
    "departureConfirm": ("출발", "출발확정", "출발예정"),
    "priceConfirm": ("가격", "가격확정", "가격예정"),
    "scheduleConfirm": ("일정", "일정확정", "일정예정"),
    "hotelConfirm": ("호텔", "호텔확정", "호텔예정"),
    "flightConfirm": ("항공", "항공확정", "항공예정"),
}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _yn_status(value: Any, confirmed: str, pending: str) -> str:
    return confirmed if value == "Y" else pending


def _status_flags(detail: dict[str, Any]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for field, (name, confirmed, pending) in STATUS_LABELS.items():
        flags.append(
            {
                "name": name,
                "value": _yn_status(detail.get(field), confirmed, pending),
                "raw_field": field,
                "raw_value": detail.get(field),
            }
        )
    leader_accompany = detail.get("leaderAccompany")
    leader_status = _clean(detail.get("leaderStatus"))
    leader_name = _clean(detail.get("leaderName"))
    if leader_accompany in {"Y", "P"} or leader_status or leader_name:
        flags.append(
            {
                "name": "인솔자",
                "value": _yn_status(detail.get("leaderConfirm"), "인솔자 확정", "인솔자 예정"),
                "raw_field": "leaderConfirm",
                "raw_value": detail.get("leaderConfirm"),
                "display_evidence": {
                    "leaderAccompany": leader_accompany,
                    "leaderStatus": leader_status,
                    "leaderName": leader_name,
                },
            }
        )
    return flags


def _summary_badges(raw: dict[str, Any], normalized: Any) -> list[dict[str, Any]]:
    detail = raw.get("detail", {})
    package_info = raw.get("package_info", {})
    assert isinstance(detail, dict)
    assert isinstance(package_info, dict)

    guide_fee_currency = normalized.guide_fee_currency
    guide_fee_adult = normalized.guide_fee_adult
    guide_fee = None
    if guide_fee_currency and guide_fee_adult is not None:
        guide_fee = f"가이드 경비{guide_fee_currency}{guide_fee_adult}"

    values = [
        normalized.travel_period_text or (
            f"{normalized.nights}박{normalized.days}일"
            if normalized.nights is not None and normalized.days is not None
            else None
        ),
        f"{normalized.departure_airline_name} 직항"
        if normalized.departure_airline_name and normalized.direct_flight is True
        else normalized.departure_airline_name,
        "쇼핑없음" if normalized.shopping_count == 0 else (
            f"쇼핑 {normalized.shopping_count}회" if normalized.shopping_count is not None else None
        ),
        guide_fee,
        "선택관광 있음" if normalized.optional_tour_or_not == "Y" else (
            "선택관광 없음" if normalized.optional_tour_or_not == "N" else None
        ),
        f"{detail.get('minimumDepartureNumberOfPeople')}명 이상시 인솔자 동행"
        if detail.get("minimumDepartureNumberOfPeople") and detail.get("leaderAccompany") in {"Y", "P"}
        else None,
    ]
    return [
        {"value": value, "source": "computed_from_detail_and_package_info"}
        for value in values
        if value
    ]


def _price(raw: dict[str, Any], normalized: Any) -> dict[str, Any]:
    detail = raw.get("detail", {})
    assert isinstance(detail, dict)
    return {
        "adult": {
            "total": normalized.selling_price_adult,
            "base": detail.get("sellingPriceAdult"),
            "product_total": detail.get("productPriceAdultTotalAmount"),
            "display": normalized.display_price_adult,
        },
        "child": {
            "no_bed_total": normalized.selling_price_child_no_bed,
            "extra_bed_total": normalized.selling_price_child_extra_bed,
            "product_no_bed_total": detail.get("productPriceKidNTotalAmount"),
            "product_extra_bed_total": detail.get("productPriceKidETotalAmount"),
        },
        "infant": {
            "total": normalized.selling_price_infant,
            "product_total": detail.get("productPriceToddlerTotalAmount"),
        },
        "local_join": normalized.selling_price_local_join,
    }


def _reservation_count(raw: dict[str, Any]) -> dict[str, Any]:
    detail = raw.get("detail", {})
    package_info = raw.get("package_info", {})
    assert isinstance(detail, dict)
    assert isinstance(package_info, dict)
    booking = package_info.get("booking", {})
    if not isinstance(booking, dict):
        booking = {}
    return {
        "reserved_people": detail.get("eventNumberOfPeople"),
        "booking_seats": detail.get("bookingSeatNumber"),
        "available_seats": detail.get("availableSeatNumber") or booking.get("restSeat"),
        "minimum_departure_people": detail.get("minimumDepartureNumberOfPeople") or booking.get("minSeat"),
    }


def _shopping_count(raw: dict[str, Any], normalized: Any) -> int | None:
    detail = raw.get("detail", {})
    package_info = raw.get("package_info", {})
    assert isinstance(detail, dict)
    assert isinstance(package_info, dict)
    return normalized.shopping_count if normalized.shopping_count is not None else package_info.get("shoppingCount")


def _none_if_empty(value: str) -> str | None:
    return value if value else None


def _meeting_info(raw: dict[str, Any], normalized: Any) -> dict[str, Any] | None:
    detail = raw.get("detail", {})
    assert isinstance(detail, dict)
    meeting_time = _none_if_empty(normalized.meeting_time or "")
    meeting_place = _none_if_empty(normalized.meeting_place_text)
    meeting_detail = _none_if_empty(normalized.meeting_info_text)
    meeting_image = _none_if_empty(_clean(detail.get("meetSrc")))
    if not any([meeting_time, meeting_place, meeting_detail, meeting_image]):
        return None
    return {
        "meeting_time": meeting_time,
        "meeting_place": meeting_place,
        "meeting_detail": meeting_detail,
        "meeting_image": meeting_image,
    }


def _event(event: Any) -> dict[str, Any]:
    return {
        "place_name": event.place_name,
        "service_name": event.service_name,
        "summary": event.summary,
        "detail": event.detail,
        "city_name": event.city_name,
        "country_name": event.country_name,
        "service_code": event.service_code,
        "sequence": event.sequence,
    }


def _flight(segment: Any) -> dict[str, Any]:
    return {
        "direction": segment.direction,
        "airline": segment.airline,
        "flight_no": segment.flight_no,
        "departure_city_name": segment.departure_city_name,
        "departure_date": segment.departure_date,
        "departure_time": segment.departure_time,
        "arrival_city_name": segment.arrival_city_name,
        "arrival_date": segment.arrival_date,
        "arrival_time": segment.arrival_time,
        "duration": segment.duration,
        "is_direct": segment.is_direct,
    }


def _days(normalized: Any) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    for day in normalized.schedule_days:
        schedule_items = []
        for category, events in (
            ("meal", day.meals),
            ("guide", day.guides),
            ("hotel", day.hotels),
            ("local_transport", day.transports),
            ("other", day.others),
        ):
            schedule_items.extend(
                {"category": category, **_event(event)}
                for event in events
            )
        days.append(
            {
                "day_no": day.day_no,
                "date": day.date,
                "route_headers": day.route_headers,
                "air": [_flight(segment) for segment in day.air],
                "schedule_items": schedule_items,
            }
        )
    return days


def build_extraction(group_id: str) -> dict[str, Any]:
    raw = ModeTourApiClient(settings).fetch_all(group_id)
    normalized = normalize_product(group_id, raw)
    detail = raw.get("detail", {})
    assert isinstance(detail, dict)

    hashtags = list(dict.fromkeys([*normalized.hashtags, *normalized.group_brief_keywords]))
    return {
        "group_no": group_id,
        "product_code": normalized.product_code,
        "computed_product_code": normalized.computed_product_code,
        "title": normalized.title,
        "hashtags": hashtags,
        "prices": _price(raw, normalized),
        "notice_flags": _status_flags(detail),
        "summary_badges": _summary_badges(raw, normalized),
        "travel_period": {
            "text": normalized.travel_period_text,
            "nights": normalized.nights,
            "days": normalized.days,
            "departure_date": normalized.departure_date,
            "arrival_date": normalized.arrival_date,
        },
        "air_itinerary": [_flight(segment) for segment in normalized.air_segments],
        "travel_cities": {
            "countries": normalized.country_names,
            "cities": normalized.city_names,
            "visit_cities": normalized.visit_cities,
        },
        "reservation_count": _reservation_count(raw),
        "shopping_count": _shopping_count(raw, normalized),
        "key_points": {
            "product_point": {
                "text": normalized.product_point_text,
                "items": normalized.product_point_items,
            },
            "special_benefits": normalized.special_benefits,
            "tourism": normalized.sightseeings,
            "meals": normalized.key_point_meals,
            "leader_guide": {
                "text": normalized.key_point_leader_guild,
                "guide_status": normalized.guide_status,
                "leader_status": normalized.leader_status,
                "guide_info": normalized.guide_info,
            },
            "insurance": normalized.traveler_insurance_text,
            "modetour_mileage": normalized.expected_tour_mileage_text,
        },
        "included": {
            "text": normalized.included_text,
            "items": normalized.included_items,
        },
        "excluded": {
            "text": normalized.excluded_text,
            "items": normalized.excluded_items,
        },
        "미팅정보": _meeting_info(raw, normalized),
        "days": _days(normalized),
        "source_meta": {
            "endpoints": sorted(raw.keys()),
            "raw_detail_group_number": detail.get("groupNumber"),
            "raw_reserve_status": detail.get("reserveStatus"),
            "raw_reserve_status_korean": detail.get("reserveStatusKorean"),
        },
    }


def validate_extraction(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_top = [
        "product_code",
        "group_no",
        "title",
        "hashtags",
        "prices",
        "notice_flags",
        "summary_badges",
        "travel_period",
        "air_itinerary",
        "travel_cities",
        "reservation_count",
        "shopping_count",
        "key_points",
        "included",
        "excluded",
        "미팅정보",
        "days",
    ]
    for key in required_top:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    prices = data.get("prices")
    if not isinstance(prices, dict):
        errors.append("prices must be an object")
    else:
        for key in ("adult", "child", "infant"):
            if key not in prices:
                errors.append(f"missing prices.{key}")
    days = data.get("days")
    if not isinstance(days, list) or not days:
        errors.append("days must be a non-empty list")
    else:
        for index, day in enumerate(days):
            if not isinstance(day, dict):
                errors.append(f"days[{index}] must be an object")
                continue
            for key in ("day_no", "schedule_items"):
                if key not in day:
                    errors.append(f"missing days[{index}].{key}")
    return errors


def output_path_for(group_id: str, output_dir: Path) -> Path:
    return output_dir / f"일정표_{group_id}.json"


def selected_group_ids(cli_group_ids: list[str]) -> list[str]:
    if cli_group_ids:
        return cli_group_ids
    return [group_id.strip() for group_id in HARDCODED_GROUP_IDS if group_id.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "group_ids",
        nargs="*",
        help="추출할 단체번호. 입력하지 않으면 HARDCODED_GROUP_IDS 값을 사용합니다.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="JSON 파일을 저장할 폴더입니다. 기본값은 이 스크립트가 있는 폴더입니다.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    group_ids = selected_group_ids(args.group_ids)
    if not group_ids:
        logger.error("단체번호를 입력하거나 HARDCODED_GROUP_IDS에 1개 이상 추가해야 합니다.")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for group_id in group_ids:
        data = build_extraction(group_id)
        errors = validate_extraction(data)
        if errors:
            failed = True
            for error in errors:
                logger.error("group_id=%s %s", group_id, error)
            continue
        output_path = output_path_for(group_id, args.output_dir)
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Wrote %s", output_path)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
