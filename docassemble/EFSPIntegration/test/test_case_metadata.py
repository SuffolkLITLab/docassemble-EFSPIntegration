# do not pre-load

"""Exercise shared response normalization and the shipped generic label blocks."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import yaml
from .. import case_metadata as m

BLOCKS = list(
    yaml.safe_load_all(
        (
            Path(__file__).resolve().parents[1] / "data/questions/case_metadata.yml"
        ).read_text()
    )
)


def block(block_id):
    return next(b["code"] for b in BLOCKS if b and b.get("id") == block_id)


def response(data, status=200):
    return SimpleNamespace(
        data=data, response_code=status, is_ok=lambda: 200 <= status <= 205
    )


@pytest.mark.parametrize("branch", ["selected case", "search result"])
@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        [],
        "bad",
        123,
        {"name": None},
        {"name": ""},
        {"name": " "},
        {"name": 3},
    ],
)
def test_nullable_labels_in_actual_blocks(branch, data):
    case = SimpleNamespace(court_id="child", case_type="42", category="7")
    proxy = SimpleNamespace(
        get_case_type=Mock(return_value=response(data)),
        get_case_categories=Mock(return_value=response(None)),
    )
    scope = dict(
        x=SimpleNamespace(found_case=case, found_cases=[case]),
        i=0,
        proxy_conn=proxy,
        case_labels=m.case_labels,
        court_id="parent",
    )
    exec(block("resolve " + branch + " labels"), scope)
    assert case.case_type_name is None
    assert case.case_category_name is None
    proxy.get_case_type.assert_called_once_with("child", "42")
    assert (case.case_type, case.category) == ("42", "7")


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 502, 503, -1])
def test_error_names_are_not_trusted(status):
    proxy = SimpleNamespace(
        get_case_type=Mock(return_value=response({"name": "Civil"}, status)),
        get_case_categories=Mock(
            return_value=response([{"code": "7", "name": "Summary Process"}], status)
        ),
    )
    assert m.case_labels(proxy, "court", "42", "7") == (None, None)


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        "bad",
        5,
        [None],
        [{"code": "7", "name": None}],
        [{"code": "7", "name": 6}],
    ],
)
def test_malformed_categories(data):
    proxy = SimpleNamespace(
        get_case_type=Mock(return_value=None),
        get_case_categories=Mock(return_value=response(data)),
    )
    assert m.case_labels(proxy, "court", "42", "7") == (None, None)


def test_recovery():
    proxy = SimpleNamespace(
        get_case_type=Mock(
            side_effect=[response(None), response({"name": "No Cause"})]
        ),
        get_case_categories=Mock(
            return_value=response([{"code": "7", "name": "Summary Process"}])
        ),
    )
    assert m.case_labels(proxy, "court", "42", "7") == (None, "Summary Process")
    assert m.case_labels(proxy, "court", "42", "7") == ("No Cause", "Summary Process")


def test_original_failure_reproduced():
    scope = dict(
        proxy_conn=SimpleNamespace(get_case_type=lambda *args: response(None)),
        court_id="court",
        x=SimpleNamespace(found_case=SimpleNamespace(case_type="42")),
    )
    with pytest.raises(
        AttributeError, match="'NoneType' object has no attribute 'get'"
    ):
        exec(
            "# original block\nx.found_case.case_type_name = proxy_conn.get_case_type(court_id, x.found_case.case_type).data.get('name', x.found_case.case_type)",
            scope,
        )


def test_clear_existing_labels_without_changing_filing_codes():
    first = SimpleNamespace(
        case_type="42", case_type_name="old", case_category_name="old"
    )
    second = SimpleNamespace(
        category="7", case_type_name="old", case_category_name="old"
    )
    search = SimpleNamespace(found_case=second, found_cases=[first, second])
    m.clear_case_labels(search)
    assert first.__dict__ == {"case_type": "42"}
    assert second.__dict__ == {"category": "7"}
    m.clear_case_labels(SimpleNamespace())
