from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


IssueLevel = Literal["FATAL", "ERROR", "WARN", "INFO"]
RuleStatus = Literal["passed", "failed", "not_applicable", "not_evaluated"]
InspectionStatus = Literal["ok", "partial", "error"]
CacheStatus = Literal["hit", "miss", "partial"]
Confidence = Literal["high", "medium", "low"]


class EvidenceItem(BaseModel):
    field: str
    value_excerpt: str


class Issue(BaseModel):
    rule_id: str
    level: IssueLevel
    title: str
    message: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    suggestion: str


class FlightRemark(BaseModel):
    info_name: str
    remark: str


class FlightSegment(BaseModel):
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


class ScheduleEvent(BaseModel):
    place_name: str = ""
    service_name: str
    summary: str
    detail: str
    city_name: str | None = None
    country_name: str | None = None
    service_code: str | None = None
    sequence: int | None = None


class HotelStay(BaseModel):
    day_no: int
    date: str | None = None
    hotel_name: str
    city_name: str | None = None
    country_name: str | None = None
    hotel_grade: str | None = None
    hotel_note: str | None = None


class DaySchedule(BaseModel):
    day_no: int
    date: str | None = None
    route_headers: list[str] = Field(default_factory=list)
    place_names: list[str] = Field(default_factory=list)
    schedule_hotel_text: str = ""
    air: list[FlightSegment] = Field(default_factory=list)
    meals: list[ScheduleEvent] = Field(default_factory=list)
    guides: list[ScheduleEvent] = Field(default_factory=list)
    hotels: list[ScheduleEvent] = Field(default_factory=list)
    transports: list[ScheduleEvent] = Field(default_factory=list)
    others: list[ScheduleEvent] = Field(default_factory=list)


class NormalizedProduct(BaseModel):
    product_no: str
    product_name: str
    title: str
    product_code: str | None = None
    computed_product_code: str | None = None
    prefixes: list[str] = Field(default_factory=list)
    themes: list[dict[str, str]] = Field(default_factory=list)
    group_brief_keywords: list[str] = Field(default_factory=list)
    top_badges: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    travel_period_text: str | None = None
    departure_date: str | None = None
    arrival_date: str | None = None
    nights: int | None = None
    days: int | None = None
    country_names: list[str] = Field(default_factory=list)
    city_names: list[str] = Field(default_factory=list)
    visit_cities: list[str] = Field(default_factory=list)
    departure_airline_name: str | None = None
    return_airline_name: str | None = None
    departure_flight: str | None = None
    return_flight: str | None = None
    direct_flight: bool | None = None
    air_segments: list[FlightSegment] = Field(default_factory=list)
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
    included_items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
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
    special_benefits: list[str] = Field(default_factory=list)
    product_point_text: str = ""
    product_point_items: list[str] = Field(default_factory=list)
    sightseeings: list[str] = Field(default_factory=list)
    key_point_hotels: list[str] = Field(default_factory=list)
    key_point_meals: list[str] = Field(default_factory=list)
    key_point_golfs: list[str] = Field(default_factory=list)
    key_point_leader_guild: str = ""
    business_guarantee: str = ""
    product_score: str = ""
    selling_price: str = ""
    guide_status: str | None = None
    leader_status: str | None = None
    guide_info: list[dict[str, Any]] = Field(default_factory=list)
    flight_remarks: list[FlightRemark] = Field(default_factory=list)
    coupon_count: int = 0
    coupon_titles: list[str] = Field(default_factory=list)
    hotels: list[HotelStay] = Field(default_factory=list)
    schedule_days: list[DaySchedule] = Field(default_factory=list)


class QualityScore(BaseModel):
    score: int
    grade: str


class InspectionPayload(BaseModel):
    summary: str
    normalized: NormalizedProduct
    issues: list[Issue]
    quality: QualityScore


class InspectionEnvelope(BaseModel):
    status: str
    code: str
    message: str
    group_id: str
    meta: dict[str, Any]
    result: InspectionPayload | None = None


class CompactIssue(BaseModel):
    rule_id: str
    level: IssueLevel
    title: str
    message: str
    suggestion: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class CompactFlightSummary(BaseModel):
    direction: str
    flight_no: str | None = None
    departure_city_name: str | None = None
    departure_time: str | None = None
    arrival_city_name: str | None = None
    arrival_time: str | None = None


class CompactDaySummary(BaseModel):
    day_no: int
    date: str | None = None
    route_headers: list[str] = Field(default_factory=list)
    place_names: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class CompactNormalizedProduct(BaseModel):
    product_no: str
    product_name: str
    title: str
    top_badges: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    departure_date: str | None = None
    arrival_date: str | None = None
    nights: int | None = None
    days: int | None = None
    country_names: list[str] = Field(default_factory=list)
    city_names: list[str] = Field(default_factory=list)
    departure_airline_name: str | None = None
    return_airline_name: str | None = None
    departure_flight: str | None = None
    return_flight: str | None = None
    direct_flight: bool | None = None
    shopping_count: int | None = None
    optional_tour_or_not: str | None = None
    local_required_expense_or_not: str | None = None
    local_required_expense: int | None = None
    included_items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    special_benefits: list[str] = Field(default_factory=list)
    product_point_text: str = ""
    product_point_items: list[str] = Field(default_factory=list)
    sightseeings: list[str] = Field(default_factory=list)
    key_point_hotels: list[str] = Field(default_factory=list)
    key_point_meals: list[str] = Field(default_factory=list)
    key_point_leader_guild: str = ""
    display_price_adult: int | None = None
    selling_price_adult: int | None = None
    selling_price_child_no_bed: int | None = None
    selling_price_child_extra_bed: int | None = None
    selling_price_infant: int | None = None
    coupon_count: int = 0
    coupon_titles: list[str] = Field(default_factory=list)
    hotels: list[str] = Field(default_factory=list)
    air_segments: list[CompactFlightSummary] = Field(default_factory=list)
    schedule_days: list[CompactDaySummary] = Field(default_factory=list)


class CompactInspectionPayload(BaseModel):
    summary: str
    normalized: CompactNormalizedProduct
    issues: list[CompactIssue]
    quality: QualityScore


class CompactInspectionEnvelope(BaseModel):
    status: str
    code: str
    message: str
    group_id: str
    meta: dict[str, Any]
    result: CompactInspectionPayload | None = None


class RunItineraryRequest(BaseModel):
    group_id: str


class InspectionRequest(BaseModel):
    group_id: str = Field(pattern=r"^[0-9]{6,12}$")
    force_refresh: bool = False


class InspectionEvidence(BaseModel):
    evidence_id: str
    source_endpoint: str | None = None
    source_path: str
    excerpt: str
    day_no: int | None = None


class RuleResult(BaseModel):
    rule_id: str
    status: RuleStatus
    level: IssueLevel
    title: str
    message: str = ""
    evidence: list[InspectionEvidence] = Field(default_factory=list)
    suggestion: str = ""
    deduction: int = 0
    confidence: Confidence = "high"


class DeterministicResults(BaseModel):
    issue_count: int
    results: list[RuleResult] = Field(default_factory=list)


class ProductSummary(BaseModel):
    product_no: str
    product_code: str | None = None
    computed_product_code: str | None = None
    title: str
    prefixes: list[str] = Field(default_factory=list)
    themes: list[dict[str, str]] = Field(default_factory=list)
    group_brief_keywords: list[str] = Field(default_factory=list)
    travel_period_text: str | None = None
    departure_date: str | None = None
    arrival_date: str | None = None
    nights: int | None = None
    days: int | None = None
    departure_airline_name: str | None = None
    return_airline_name: str | None = None
    departure_flight: str | None = None
    return_flight: str | None = None
    visit_cities: list[str] = Field(default_factory=list)
    shopping_count: int | None = None
    optional_tour_or_not: str | None = None
    guide_yn: str | None = None
    leader_yn: str | None = None
    guide_fee: dict[str, int | str | None] = Field(default_factory=dict)
    meeting_time: str | None = None
    meeting_place_text: str = ""
    prices: dict[str, int | None] = Field(default_factory=dict)


class SemanticPacket(BaseModel):
    packet_id: str
    rule_ids: list[str]
    claims: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[InspectionEvidence] = Field(default_factory=list)
    guards: list[str] = Field(default_factory=list)
    max_output_issues: int = 3


class ScoringSummary(BaseModel):
    base_score: int = 100
    deterministic_deduction: int = 0


class SourceSummary(BaseModel):
    source_hash: str
    rule_version: str
    prompt_version: str
    cache_status: CacheStatus
    fetched_at: str


class CollectionPlanSummary(BaseModel):
    required: list[str] = Field(default_factory=list)
    conditional: list[str] = Field(default_factory=list)
    skipped: list[dict[str, str]] = Field(default_factory=list)


class V3InspectionResponse(BaseModel):
    schema_version: str
    inspection_id: str
    status: InspectionStatus
    group_id: str
    product: ProductSummary
    inspection_context: dict[str, Any] = Field(default_factory=dict)
    deterministic: DeterministicResults
    semantic_packets: list[SemanticPacket] = Field(default_factory=list)
    scoring: ScoringSummary
    source: SourceSummary
    collection_plan: CollectionPlanSummary
    warnings: list[str] = Field(default_factory=list)


class EvidenceResponse(BaseModel):
    inspection_id: str
    evidence: list[InspectionEvidence] = Field(default_factory=list)
