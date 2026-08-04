from __future__ import annotations

import re
from typing import Any

from .html_utils import strip_html
from .models import DaySchedule, FlightRemark, FlightSegment, HotelStay, NormalizedProduct, ScheduleEvent


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in ("Y", "y", "true", "True", 1):
        return True
    if value in ("N", "n", "false", "False", 0):
        return False
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"[^\d-]", "", value)
        if digits in ("", "-"):
            return None
        try:
            return int(digits)
        except ValueError:
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _split_items(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.split(r"[\n\r•·,|/]+", text)
    return [token.strip(" -\t") for token in tokens if token.strip(" -\t")]


def _extract_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return _split_items(value)
    if isinstance(value, list):
        collected_list: list[str] = []
        for item in value:
            if isinstance(item, str):
                collected_list.extend(_split_items(item))
            elif isinstance(item, dict):
                for key in ("name", "title", "text", "label", "value", "summary", "desc", "description"):
                    if item.get(key):
                        collected_list.extend(_split_items(_clean_text(item.get(key))))
                        break
                if item.get("prefixes"):
                    collected_list.extend(_extract_strings(item.get("prefixes")))
        return [item for item in (token.strip() for token in collected_list) if item]
    if isinstance(value, dict):
        collected_dict: list[str] = []
        if value.get("prefixes"):
            collected_dict.extend(_extract_strings(value.get("prefixes")))
        for key in ("name", "title", "text", "label", "value", "summary", "desc", "description"):
            if value.get(key):
                collected_dict.extend(_split_items(_clean_text(value.get(key))))
        return [item for item in (token.strip() for token in collected_dict) if item]
    return []


def _clean_items(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        compact = _clean_text(item)
        if not compact:
            continue
        upper = compact.upper()
        if "FONT-FAMILY" in upper or "TELERIK-STYLE-TYPE" in upper or upper.startswith("UNTITLED P "):
            continue
        cleaned.append(compact)
    return cleaned


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _extract_product_point_items(*values: Any) -> list[str]:
    items: list[str] = []
    for value in values:
        text = strip_html(value)
        if not text:
            continue
        for line in re.split(r"[\r\n]+", text):
            compact = _clean_text(line).lstrip("-•■▶▣")
            compact = _clean_text(compact)
            if len(compact) < 2:
                continue
            items.append(compact)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _extract_hashtags(*values: Any) -> list[str]:
    tags: list[str] = []
    for value in values:
        for item in _extract_strings(value):
            compact = _clean_text(item)
            if not compact:
                continue
            if compact.startswith("#"):
                tags.append(compact)
            elif " #" in compact or compact.count("#") >= 1:
                tags.extend(part for part in compact.split() if part.startswith("#"))
    deduped: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = tag.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _extract_hash_keywords(value: Any) -> list[str]:
    keywords: list[str] = []
    for item in _extract_strings(value):
        if "#" not in item:
            keywords.append(item)
            continue
        parts = re.findall(r"#[^#\s]+(?:\s+[^#\s]+)*", item)
        keywords.extend(part.strip() for part in parts if part.strip())
    return _clean_items(keywords)


def _extract_themes(value: Any) -> list[dict[str, str]]:
    themes: list[dict[str, str]] = []
    for item in _as_list(value):
        if not isinstance(item, dict):
            continue
        theme_id = _clean_text(item.get("themeId") or item.get("themeID") or item.get("id"))
        theme_name = _clean_text(item.get("themeName") or item.get("name") or item.get("title"))
        if not theme_id and not theme_name:
            continue
        themes.append({"theme_id": theme_id, "theme_name": theme_name})
    return themes


def _event_from_place(place: dict[str, Any]) -> ScheduleEvent:
    return ScheduleEvent(
        place_name=_clean_text(place.get("itiPlaceName") or place.get("placeNameK") or place.get("placeNameE")),
        service_name=_clean_text(place.get("itiServiceName")),
        summary=_clean_text(place.get("itiSummaryDes") or place.get("serviceWITHSummary")),
        detail=strip_html(place.get("itiDetailDes") or place.get("detailDes") or place.get("serviceExplaination")),
        city_name=place.get("cityName"),
        country_name=place.get("countryName"),
        service_code=place.get("itiServiceCode"),
        sequence=place.get("itiSeq"),
    )


def _extract_flight_segments(route_info: dict[str, Any]) -> list[FlightSegment]:
    segments: list[FlightSegment] = []
    direction = _clean_text(route_info.get("flightTypeName") or "UNKNOWN")
    for item in _as_list(route_info.get("item")):
        if not isinstance(item, dict):
            continue
        airline = item.get("transportName")
        flight_no = item.get("departureFlight")
        dep_city = item.get("departureCityName")
        arr_city = item.get("arrivalCityName")
        if not any([airline, flight_no, dep_city, arr_city]):
            continue
        segments.append(
            FlightSegment(
                direction=direction,
                airline=airline,
                flight_no=flight_no,
                departure_city_name=dep_city,
                departure_city_code=item.get("departureCity"),
                departure_date=item.get("departureDate"),
                departure_time=item.get("departureTime"),
                arrival_city_name=arr_city,
                arrival_city_code=item.get("arrivalCity"),
                arrival_date=item.get("arrivalDate"),
                arrival_time=item.get("arrivalTime"),
                duration=item.get("departureFlightDuration"),
                is_direct=_to_bool(route_info.get("isDirectFlight")),
                is_transit=_to_bool(route_info.get("isTransit")),
            )
        )
    return segments


def normalize_product(product_no: str, raw: dict[str, Any]) -> NormalizedProduct:
    package_info = raw.get("package_info", {})
    detail = raw.get("detail", {})
    schedule = raw.get("schedule", {})
    hotels_raw = raw.get("hotels", [])
    flight_remarks_raw = raw.get("flight_remarks", [])
    key_points = raw.get("key_points", {})
    package_badges = _extract_strings(package_info.get("badges"))
    prefixes = _dedupe(
        _clean_items(
            [
                *_extract_strings(package_info.get("prefixes")),
                *_extract_strings(package_info.get("prefix")),
                *_extract_strings(package_info.get("prefixPName")),
                *_extract_strings(package_info.get("badges")),
                *_extract_strings(detail.get("prefixName")),
            ]
        )
    )
    group_brief_keywords = _dedupe(_extract_hash_keywords(detail.get("groupBriefKeyword")))
    visit_cities = [_clean_text(city) for city in _as_list(detail.get("visitCities")) if _clean_text(city)]
    hashtags = _extract_hashtags(
        raw.get("tags"),
        detail.get("tags"),
        detail.get("hashTags"),
        detail.get("hashtags"),
        package_info.get("tags"),
        package_info.get("hashTags"),
        key_points.get("tags"),
        key_points.get("hashTags"),
    )

    schedule_days: list[DaySchedule] = []
    city_names: set[str] = set()
    all_air_segments: list[FlightSegment] = []

    for day in _as_list(schedule.get("scheduleItemList")):
        if not isinstance(day, dict):
            continue
        route_headers = [str(x) for x in _as_list(day.get("placeHeader")) if str(x).strip()]
        city_names.update(route_headers)
        day_air_segments = _extract_flight_segments(day.get("listAirRouteInfo") or {})
        all_air_segments.extend(day_air_segments)
        for segment in day_air_segments:
            if segment.departure_city_name:
                city_names.add(segment.departure_city_name)
            if segment.arrival_city_name:
                city_names.add(segment.arrival_city_name)
        hotel_events = [_event_from_place(x) for x in _as_list(day.get("listHotelPlace")) if isinstance(x, dict)]
        meals = [_event_from_place(x) for x in _as_list(day.get("listMealPlace")) if isinstance(x, dict)]
        guides = [_event_from_place(x) for x in _as_list(day.get("listGuidePlace")) if isinstance(x, dict)]
        transports = [_event_from_place(x) for x in _as_list(day.get("listTransportPlace")) if isinstance(x, dict)]
        other_actions = day.get("otherActions")
        if other_actions is None:
            other_actions = day.get("ortherActions")
        others = [_event_from_place(x) for x in _as_list(other_actions) if isinstance(x, dict)]
        place_names = [event.place_name for event in [*hotel_events, *meals, *guides, *transports, *others] if event.place_name]
        schedule_days.append(
            DaySchedule(
                day_no=int(day.get("first") or 0),
                date=day.get("date"),
                route_headers=route_headers,
                place_names=place_names,
                schedule_hotel_text=_clean_text(day.get("scheduleHotel")),
                air=day_air_segments,
                meals=meals,
                guides=guides,
                hotels=hotel_events,
                transports=transports,
                others=others,
            )
        )

    hotels: list[HotelStay] = []
    for hotel_day in _as_list(hotels_raw):
        if not isinstance(hotel_day, dict):
            continue
        day_no = int(hotel_day.get("first") or 0)
        for place in _as_list(hotel_day.get("listHotelPlaceData")):
            if not isinstance(place, dict):
                continue
            city_name = place.get("cityName")
            if city_name:
                city_names.add(city_name)
            hotels.append(
                HotelStay(
                    day_no=day_no,
                    date=hotel_day.get("date"),
                    hotel_name=_clean_text(place.get("placeNameK") or place.get("itiPlaceName")),
                    city_name=city_name,
                    country_name=place.get("countryName"),
                    hotel_grade=_clean_text(place.get("highlightDes")),
                    hotel_note=_clean_text(place.get("contactWay") or place.get("itiSummaryDes")),
                )
            )

    country_names = {
        value
        for value in [
            package_info.get("air", {}).get("countryName"),
            *[hotel.country_name for hotel in hotels if hotel.country_name],
        ]
        if value
    }

    flight_remarks = [
        FlightRemark(info_name=_clean_text(row.get("infoName")), remark=_clean_text(row.get("remark")))
        for row in _as_list(flight_remarks_raw)
        if isinstance(row, dict)
    ]
    coupons_raw = _as_list(raw.get("coupons", []))
    coupon_titles = _clean_items(_extract_strings(coupons_raw))
    included_text = strip_html(detail.get("includedNote"))
    excluded_text = strip_html(detail.get("unincludedNote"))
    notice_text = strip_html(detail.get("noticeNote"))
    product_point_text = strip_html(
        detail.get("travelRecommendNote")
        or detail.get("generalBonusNote")
        or detail.get("specialEventNote")
    )
    product_point_items = _extract_product_point_items(
        detail.get("travelRecommendNote"),
        detail.get("generalBonusNote"),
        detail.get("specialEventNote"),
    )
    included_items = _clean_items(_extract_strings(included_text))
    excluded_items = _clean_items(_extract_strings(excluded_text))
    package_price = package_info.get("price", {}) if isinstance(package_info.get("price"), dict) else {}
    before_discount = package_info.get("beforeDicount") or package_info.get("beforeDiscount") or {}
    package_before_discount = before_discount if isinstance(before_discount, dict) else {}

    return NormalizedProduct(
        product_no=product_no,
        product_name=_clean_text(detail.get("productName") or package_info.get("pName")),
        title=_clean_text(detail.get("productName") or package_info.get("pName")),
        product_code=_clean_text(detail.get("productCode") or package_info.get("pcode")) or None,
        computed_product_code=_clean_text(package_info.get("computedProductCode")) or None,
        prefixes=prefixes,
        themes=_extract_themes(package_info.get("themes")),
        group_brief_keywords=group_brief_keywords,
        top_badges=package_badges,
        hashtags=hashtags,
        travel_period_text=_clean_text(detail.get("travelPeriod")) or None,
        departure_date=detail.get("departureDate") or package_info.get("date", {}).get("sdate"),
        arrival_date=detail.get("arrivalDate") or package_info.get("date", {}).get("edate"),
        nights=detail.get("travelNight") or package_info.get("date", {}).get("night"),
        days=detail.get("travelDays") or package_info.get("date", {}).get("days"),
        country_names=sorted(country_names),
        city_names=sorted(x for x in city_names if x),
        visit_cities=visit_cities,
        departure_airline_name=_clean_text(detail.get("departureAirlineName") or package_info.get("air", {}).get("airLineName")) or None,
        return_airline_name=_clean_text(detail.get("arrivalAirlineName")) or None,
        departure_flight=_clean_text(detail.get("departureFlight") or package_info.get("air", {}).get("startAir")) or None,
        return_flight=_clean_text(detail.get("arrivalFlight")) or None,
        direct_flight=_to_bool(detail.get("directFlightOrNot")),
        air_segments=all_air_segments,
        guide_yn=_clean_text(package_info.get("guideYn")) or None,
        leader_yn=_clean_text(package_info.get("leaderYn")) or None,
        shopping_count=detail.get("shoppingTimes", package_info.get("shoppingCount")),
        optional_tour_or_not=_clean_text(detail.get("optionalTourOrNot")) or None,
        local_required_expense_or_not=_clean_text(detail.get("localRequiredExpenseOrNot")) or None,
        local_required_expense=_to_int(detail.get("localRequiredExpense")),
        guide_fee_currency=_clean_text(detail.get("localRequiredExpenseCall")) or None,
        guide_fee_adult=_to_int(detail.get("localRequiredExpense")),
        guide_fee_child=_to_int(detail.get("localRequiredExpenseKid")),
        guide_fee_infant=_to_int(detail.get("localRequiredExpenseToddler")),
        meeting_time=_clean_text(detail.get("meetingTime")) or None,
        meeting_place_text=strip_html(detail.get("meetingPlace2")),
        meeting_info_text=strip_html(detail.get("meetingInfo")),
        notice_text=notice_text,
        included_text=included_text,
        excluded_text=excluded_text,
        included_items=included_items,
        excluded_items=excluded_items,
        shopping_text=strip_html(detail.get("shoppingNote")),
        traveler_insurance_text=strip_html(
            detail.get("travelerInsuranceResponsibility") or key_points.get("travelerInsuranceInfo")
        ),
        expected_tour_mileage_text=_clean_text(
            detail.get("accumulationExpectedTourMileage")
            or key_points.get("accumulationExpectedTourMileage")
            or package_info.get("accumulationExpectedTourMileage")
        ),
        display_price_adult=_to_int(
            _first_not_none(
                package_price.get("adult"),
                package_price.get("adultPrice"),
                package_info.get("adultPrice"),
                package_info.get("priceAdult"),
            )
        ),
        before_discount_price_adult=_to_int(
            _first_not_none(
                package_before_discount.get("adult"),
                package_before_discount.get("adultPrice"),
                package_info.get("beforeDiscountAdultPrice"),
            )
        ),
        selling_price_adult=_to_int(
            _first_not_none(
                detail.get("sellingPriceAdultTotalAmount"),
                detail.get("sellingPriceAdult"),
                key_points.get("sellingPrice"),
            )
        ),
        selling_price_child_no_bed=_to_int(
            _first_not_none(detail.get("sellingPriceKidNTotalAmount"), detail.get("sellingPriceKidN"))
        ),
        selling_price_child_extra_bed=_to_int(
            _first_not_none(detail.get("sellingPriceKidETotalAmount"), detail.get("sellingPriceKidE"))
        ),
        selling_price_infant=_to_int(
            _first_not_none(detail.get("sellingPriceToddlerTotalAmount"), detail.get("sellingPriceToddler"))
        ),
        selling_price_local_join=_to_int(
            _first_not_none(detail.get("sellingPriceLandTotalAmount"), detail.get("sellingPriceLand"))
        ),
        special_benefits=[_clean_text(x) for x in _as_list(key_points.get("specialBenefits")) if _clean_text(x)],
        product_point_text=product_point_text,
        product_point_items=product_point_items,
        sightseeings=[_clean_text(x) for x in _as_list(key_points.get("sightseeings")) if _clean_text(x)],
        key_point_hotels=[_clean_text(x) for x in _as_list(key_points.get("hotels")) if _clean_text(x)],
        key_point_meals=[_clean_text(x) for x in _as_list(key_points.get("meals")) if _clean_text(x)],
        key_point_golfs=[_clean_text(x) for x in _as_list(key_points.get("golfs")) if _clean_text(x)],
        key_point_leader_guild=_clean_text(key_points.get("leaderGuild")),
        business_guarantee=_clean_text(key_points.get("businessGuarantee")),
        product_score=_clean_text(key_points.get("productScore")),
        selling_price=_clean_text(key_points.get("sellingPrice")),
        guide_status=_clean_text(key_points.get("leaderGuildStatus")) or None,
        leader_status=_clean_text(key_points.get("leaderStatus")) or None,
        guide_info=[x for x in _as_list(key_points.get("guideInfo")) if isinstance(x, dict)],
        flight_remarks=flight_remarks,
        coupon_count=len(coupon_titles),
        coupon_titles=coupon_titles,
        hotels=hotels,
        schedule_days=schedule_days,
    )
