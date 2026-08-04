from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from .auth import capture_base_headers
from .config import Settings

logger = logging.getLogger(__name__)


class ModeTourApiError(RuntimeError):
    """Raised when a ModeTour API call fails."""


class ModeTourAuthExpiredError(ModeTourApiError):
    """Raised when ModeTour headers appear to be expired or rejected."""


@dataclass(frozen=True)
class EndpointSpec:
    name: str
    path: str


class ModeTourApiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_headers = capture_base_headers(settings)
        self._endpoints = (
            EndpointSpec("package_info", "/Package/GetPackageInfo"),
            EndpointSpec("schedule", "/Package/GetScheduleList"),
            EndpointSpec("detail", "/Package/GetProductDetailInfo"),
            EndpointSpec("hotels", "/Package/GetHotelList"),
            EndpointSpec("flight_remarks", "/Package/GetFlightRemarkList"),
            EndpointSpec("key_points", "/Package/GetProductKeyPointInfo"),
            EndpointSpec("coupons", "/Coupon/GetPackageCouponList"),
        )
        self._endpoint_by_name = {endpoint.name: endpoint for endpoint in self._endpoints}

    def _headers_for_product(self, product_no: str) -> dict[str, str]:
        headers = dict(self._base_headers)
        headers["x-incomming-pathname"] = f"/product-common/{product_no}?type=group"
        return headers

    def refresh_headers(self) -> None:
        logger.warning("Refreshing ModeTour headers after an authentication failure.")
        self._base_headers = capture_base_headers(self._settings, force_refresh=True)

    def _is_auth_failure(self, response: requests.Response) -> bool:
        if response.status_code in (401, 403):
            return True
        text = response.text[:500].lower()
        return any(token in text for token in ("unauthorized", "forbidden", "auth", "apikey", "api key"))

    def _fetch_one(self, spec: EndpointSpec, product_no: str) -> Any:
        url = f"{self._settings.base_url}{spec.path}"
        headers = self._headers_for_product(product_no)
        logger.info("Fetching %s for productNo=%s", spec.name, product_no)
        started_at = time.perf_counter()
        response = requests.get(
            url,
            params={"productNo": product_no},
            headers=headers,
            timeout=self._settings.request_timeout_seconds,
        )
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        content_length = len(response.content)
        logger.info(
            "ModeTour endpoint metric endpoint=%s productNo=%s status_code=%d elapsed_ms=%d content_length=%d",
            spec.name,
            product_no,
            response.status_code,
            elapsed_ms,
            content_length,
        )
        if not response.ok:
            if self._is_auth_failure(response):
                raise ModeTourAuthExpiredError(
                    f"{spec.name} authentication failed with status {response.status_code}."
                )
            raise ModeTourApiError(
                f"{spec.name} failed with status {response.status_code}: {response.text[:300]}"
            )
        data = response.json()
        if not isinstance(data, dict) or "result" not in data:
            raise ModeTourApiError(f"{spec.name} returned an unexpected response shape.")
        return data["result"]

    def fetch_endpoints(self, product_no: str, endpoint_names: tuple[str, ...]) -> dict[str, Any]:
        started_at = time.perf_counter()
        results: dict[str, Any] = {}
        endpoints = tuple(self._endpoint_by_name[name] for name in endpoint_names)
        max_workers = min(len(endpoints), 8)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_spec = {
                executor.submit(self._fetch_one, spec, product_no): spec for spec in endpoints
            }
            try:
                for future in concurrent.futures.as_completed(future_to_spec):
                    spec = future_to_spec[future]
                    results[spec.name] = future.result()
            except Exception:
                for future in future_to_spec:
                    future.cancel()
                raise

        elapsed = time.perf_counter() - started_at
        logger.info("Fetched %s upstream endpoints for productNo=%s in %.2fs", len(results), product_no, elapsed)
        return {spec.name: results[spec.name] for spec in endpoints}

    def fetch_core(self, product_no: str) -> dict[str, Any]:
        return self._fetch_with_optional_refresh(product_no, ("package_info", "schedule", "detail", "key_points"))

    def fetch_all(self, product_no: str) -> dict[str, Any]:
        return self._fetch_with_optional_refresh(product_no, tuple(spec.name for spec in self._endpoints))

    def _fetch_with_optional_refresh(self, product_no: str, endpoint_names: tuple[str, ...]) -> dict[str, Any]:
        try:
            return self.fetch_endpoints(product_no, endpoint_names)
        except ModeTourAuthExpiredError:
            self.refresh_headers()
            return self.fetch_endpoints(product_no, endpoint_names)
