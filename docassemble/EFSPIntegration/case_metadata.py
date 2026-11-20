"""Resolve optional case labels without treating raw codes as verified names.

Names are None when the endpoint fails or returns malformed/empty metadata.
Callers own decisions about eligibility, retry, and manual completion.
"""

from collections.abc import Mapping
import logging
from typing import Any, Optional, Tuple
from .py_efsp_client import EfspConnection

__all__ = ["case_labels", "clear_case_labels"]


def _name(data: object) -> Optional[str]:
    value = data.get("name") if isinstance(data, Mapping) else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def case_labels(
    proxy: EfspConnection, court_id: str, case_type: str, category: str
) -> Tuple[Optional[str], Optional[str]]:
    """Return validated names (None when unavailable); never classify raw codes."""
    response = proxy.get_case_type(court_id, case_type)
    type_name = (
        _name(response.data) if response is not None and response.is_ok() else None
    )
    categories = proxy.get_case_categories(court_id, fileable_only=False, timing=None)
    category_name = None
    if (
        categories is not None
        and categories.is_ok()
        and isinstance(categories.data, list)
    ):
        category_name = next(
            (
                _name(item)
                for item in categories.data
                if isinstance(item, Mapping) and str(item.get("code")) == str(category)
            ),
            None,
        )
    if type_name is None or category_name is None:
        logging.getLogger(__name__).warning(
            "efiling.case_labels court=%s type=%s status=%s payload=%s "
            "category_status=%s category_payload=%s request=%s",
            court_id,
            case_type,
            response.response_code if response is not None else None,
            type(response.data).__name__ if response is not None else "NoneType",
            categories.response_code if categories is not None else None,
            type(categories.data).__name__ if categories is not None else "NoneType",
            getattr(response, "req_id", None),
        )
    return type_name, category_name


def clear_case_labels(search: Any) -> None:
    """Invalidate existing labels without triggering docassemble dependency resolution.

    Call once per request, or before an explicit retry/case edit, before consuming
    labels and derived decisions. The caller controls when refresh is needed.
    """
    for case in [search.__dict__.get("found_case")] + list(
        search.__dict__.get("found_cases") or []
    ):
        if case is not None:
            case.__dict__.pop("case_type_name", None)
            case.__dict__.pop("case_category_name", None)
