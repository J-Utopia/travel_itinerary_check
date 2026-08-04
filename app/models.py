from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FlightRemark:
    info_name: str
    remark: str


@dataclass
class FlightSegment:
    direction: str
    airline: str | None = None
    flight_no: str | None = None
    departure_city_name: str | None = None
    departure_city_code: str | None = None
    departure_date: str | None = None
    departure_time: str | None = None
    arrival_city_name: str | None = None
    arrival_city_code: str | None = None
    arrival_date: str | None = None
    arrival_time: str | None = None
    duration: str | None = None
    is_direct: bool | None = None
    is_transit: bool | None = None


@dataclass
class ScheduleEvent:
    service_name: str
    summary: str
    detail: str
    place_name: str = ""
    city_name: str | None = None
    country_name: str | None = None
    service_code: str | None = None
    sequence: int | None = None


@dataclass
class HotelStay:
    day_no: int
    hotel_name: str
    date: str | None = None
    city_name: str | None = None
    country_name: str | None = None
    hotel_grade: str | None = None
    hotel_note: str | None = None


@dataclass
class DaySchedule:
    day_no: int
    date: str | None = None
    route_headers: list[str] = field(default_factory=list)
    place_names: list[str] = field(default_factory=list)
    schedule_hotel_text: str = ""
    air: list[FlightSegment] = field(default_factory=list)
    meals: list[ScheduleEvent] = field(default_factory=list)
    guides: list[ScheduleEvent] = field(default_factory=list)
    hotels: list[ScheduleEvent] = field(default_factory=list)
    transports: list[ScheduleEvent] = field(default_factory=list)
    others: list[ScheduleEvent] = field(default_factory=list)


@dataclass
class NormalizedProduct:
    product_no: str
    product_name: str
    title: str
    product_code: str | None = None
    computed_product_code: str | None = None
    prefixes: list[str] = field(default_factory=list)
    themes: list[dict[str, str]] = field(default_factory=list)
    group_brief_keywords: list[str] = field(default_factory=list)
    top_badges: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    travel_period_text: str | None = None
    departure_date: str | None = None
    arrival_date: str | None = None
    nights: int | None = None
    days: int | None = None
    country_names: list[str] = field(default_factory=list)
    city_names: list[str] = field(default_factory=list)
    visit_cities: list[str] = field(default_factory=list)
    departure_airline_name: str | None = None
    return_airline_name: str | None = None
    departure_flight: str | None = None
    return_flight: str | None = None
    direct_flight: bool | None = None
    air_segments: list[FlightSegment] = field(default_factory=list)
    guide_yn: str | None = None
    leader_yn: str | None = None
    shopping_count: int | None = None
    optional_tour_or_not: str | None = None
    local_required_expense_or_not: str | None = None
    local_required_expense: int | None = None
    guide_fee_currency: str | None = None
    guide_fee_adult: int | None = None
    guide_fee_child: int | None = None
    guide_fee_infant: int | None = None
    meeting_time: str | None = None
    meeting_place_text: str = ""
    meeting_info_text: str = ""
    notice_text: str = ""
    included_text: str = ""
    excluded_text: str = ""
    included_items: list[str] = field(default_factory=list)
    excluded_items: list[str] = field(default_factory=list)
    shopping_text: str = ""
    traveler_insurance_text: str = ""
    expected_tour_mileage_text: str = ""
    display_price_adult: int | None = None
    before_discount_price_adult: int | None = None
    selling_price_adult: int | None = None
    selling_price_child_no_bed: int | None = None
    selling_price_child_extra_bed: int | None = None
    selling_price_infant: int | None = None
    selling_price_local_join: int | None = None
    special_benefits: list[str] = field(default_factory=list)
    product_point_text: str = ""
    product_point_items: list[str] = field(default_factory=list)
    sightseeings: list[str] = field(default_factory=list)
    key_point_hotels: list[str] = field(default_factory=list)
    key_point_meals: list[str] = field(default_factory=list)
    key_point_golfs: list[str] = field(default_factory=list)
    key_point_leader_guild: str = ""
    business_guarantee: str = ""
    product_score: str = ""
    selling_price: str = ""
    guide_status: str | None = None
    leader_status: str | None = None
    guide_info: list[dict[str, Any]] = field(default_factory=list)
    flight_remarks: list[FlightRemark] = field(default_factory=list)
    coupon_count: int = 0
    coupon_titles: list[str] = field(default_factory=list)
    hotels: list[HotelStay] = field(default_factory=list)
    schedule_days: list[DaySchedule] = field(default_factory=list)
