"""
A group of methods that were code blocks in various parts of the EFSP
package, but for better python tooling support, were moved here.
"""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Tuple,
    Optional,
    NamedTuple,
    Iterable,
    Union,
    TypedDict,
)
from datetime import datetime

from docassemble.base.util import CustomDataType, DAObject, DAList, log, word
from .conversions import (
    parse_case_info,
    fetch_case_info,
    chain_xml,
    log_error_and_notify,
)
from docassemble.AssemblyLine.al_general import ALPeopleList, ALIndividual


class EFCaseSearch(DAObject):
    """A data-class that has holds all of the information and state for a single case search"""

    court_id: str
    can_file_non_indexed_case: bool
    do_what_choice: str
    found_case: DAObject
    case_was_found: bool

    def search_went_wrong(self) -> bool:
        """Returns true if something errored during the case search process"""
        if (
            hasattr(self, "docket_case_response")
            and not self.docket_case_response.is_ok()
        ):
            return True
        if (
            hasattr(self, "found_cases")
            and hasattr(self.found_cases, "resp_ok")
            and not self.found_cases.resp_ok
        ):
            return True
        return False

    def get_lookup_choices(
        self, can_file_non_indexed_case: bool
    ) -> List[Dict[str, str]]:
        """Returns the DA choice list of what ways you are allowed to search for a case;
        By default, this is "party_search", and "docket_lookup", and depending on the
        court, it could also include "non_indexed_case".

        Not passed as direct arguments, but the object attributes `party_search_choice`,
        `docket_lookup_choice`, and `non_indexed_choice` are the user-facing labels
        for each choice.
        """
        lookup_choices = [
            {"party_search": str(self.party_search_choice)},
            {"docket_lookup": str(self.docket_lookup_choice)},
        ]
        if can_file_non_indexed_case:
            lookup_choices.append({"non_indexed_case": str(self.non_indexed_choice)})
        return lookup_choices


_visible_password_js = """
  $(document).on('daPageLoad', function() {
    $('input[type="ALVisiblePassword"]').each(function() {
      var thisElement = this;
      $(thisElement).attr("type", "password");
      var checkbox_div = $('<div></div>');
      var checkbox_input = $('<input type="checkbox" id="idk-check">');
      var checkbox_label = $('<label for="idk-check" style="margin-left:7px">Show password</label>');
      $(checkbox_input).on('change', function() {
        if (this.checked) {
          $(thisElement).attr('type', 'text');
        } else {
          $(thisElement).attr('type', 'password');
        }
      })
      $(thisElement).after(checkbox_div);
      $(checkbox_div).append(checkbox_input);
      $(checkbox_div).append(checkbox_label);
    })
  });
"""


class ALVisiblePassword(CustomDataType):
    name = "ALVisiblePassword"
    input_type = "ALVisiblePassword"
    javascript = _visible_password_js


def address_fields_with_defaults(
    proxy_conn, person: ALIndividual, is_admin: bool, **kwargs
):
    address_fields = person.address_fields(**kwargs)
    # Efiling requires zip most of the time, enough for us to require it
    for field in address_fields:
        if field.get("field", "").endswith(".zip"):
            field["required"] = True  # type: ignore
    if is_admin:
        # Don't autofill if the person is an admin
        return address_fields
    firm_info = proxy_conn.get_firm()
    if firm_info.is_ok():
        if "address" in firm_info.data:
            for field in address_fields:
                if field.get("field", "").endswith(".address"):
                    field["default"] = firm_info.data["address"].get("addressLine1")
                if field.get("field", "").endswith(".unit"):
                    field["default"] = firm_info.data["address"].get("addressLine2")
                if field.get("field", "").endswith(".city"):
                    field["default"] = firm_info.data["address"].get("city")
                if field.get("field", "").endswith(".state"):
                    field["default"] = firm_info.data["address"].get("state")
                if field.get("field", "").endswith(".zip"):
                    field["default"] = firm_info.data["address"].get("zipCode")
    return address_fields


FieldEntry = TypedDict(
    "FieldEntry",
    {
        "label": str,
        "field": str,
        "datatype": str,
        "rows": int,
        "help": str,
        "show if": Union[str, Dict[str, str]],
        "hide if": str,
        "input type": str,
        "default": str,
        "code": str,
        "address autocomplete": bool,
        "choices": Union[List[str], Dict[str, str]],
        "required": bool,
    },
    total=False,
)
Fields = List[FieldEntry]


def contact_fields_with_defaults(
    proxy_conn, person: ALIndividual, is_admin: bool, can_check_efile: bool
):
    contact_fields: List[FieldEntry] = [
        {
            "label": word("Mobile number"),
            "field": person.attr_name("mobile_number"),
            "required": False,
        },
        {
            "label": word("Other phone number"),
            "field": person.attr_name("phone_number"),
            "required": False,
        },
        {
            "label": word("Email address"),
            "field": person.attr_name("email"),
            "datatype": "email",
            # Email is required if the user wants to efile,
            # and we have to be able to attempt efiling, meaning the court has to be right
            "required": can_check_efile,
        },
        {
            "label": word("Other ways to reach you"),
            "field": person.attr_name("other_contact_method"),
            "input type": "area",
            "required": False,
            "help": word(
                """
If you do not have a phone number or email, provide
specific contact instructions. For example, use a friend's phone number.
But the friend must be someone you can rely on to give you a
message.
      """
            ),
        },
    ]
    if is_admin or not can_check_efile:
        return contact_fields

    user_info = proxy_conn.get_user()
    if user_info.is_ok() and "email" in user_info.data:
        for field in contact_fields:
            if field.get("field", "").endswith(".email"):
                field["default"] = user_info.data.get("email")
    firm_info = proxy_conn.get_firm()
    if firm_info.is_ok() and "phoneNumber" in firm_info.data:
        for field in contact_fields:
            if field.get("field", "").endswith(".phone_number"):
                field["default"] = firm_info.data.get("phoneNumber")
    return contact_fields


def num_case_choices() -> int:
    """The number of cases that someone should have to choose between if there are too many.
    Mostly to limit the amount of up-front waiting someone will have to do."""
    return 8


def search_case_by_name(
    *,
    proxy_conn,
    var_name: str = None,
    court_id: str,
    somebody,
    filter_fn: Callable[[Any], bool],
    roles=None,
) -> Tuple[bool, DAList]:
    """Searches for cases by party name. If there are more than 10 cases found, we don't
    add all of the detailed information about the case, just for the first few cases"""
    if not var_name:
        var_name = "found_cases"
    found_cases = DAList(var_name, object_type=DAObject, auto_gather=False)
    get_cases_response = proxy_conn.get_cases(
        court_id, person=somebody, docket_number=None
    )
    cms_connection_issue = get_cases_response.response_code == 203
    if get_cases_response.is_ok():
        found_cases.resp_ok = True
        # Reversed because cases tend to be returned oldest to newest from Tyler,
        # and people aren't likely to be looking for cases from pre-2000
        for idx, entry in enumerate(reversed(get_cases_response.data)):
            new_case = found_cases.appendObject()
            should_fetch = idx < num_case_choices()
            parse_case_info(
                proxy_conn, new_case, entry, court_id, fetch=should_fetch, roles=roles
            )
            # Allows users to control what cases are shown as options
            if not filter_fn(new_case):
                found_cases.pop()
    else:
        log_error_and_notify(
            "get_cases_response failed when searching for case", get_cases_response
        )
        found_cases.resp_ok = False
    found_cases.gathered = True
    return cms_connection_issue, found_cases


def shift_case_select_window(
    proxy_conn,
    found_cases: DAList,
    *,
    direction: str,
    start_idx: int,
    end_idx: int,
    roles: dict = None,
) -> Tuple[int, int]:
    """Specifically used in case_search.yml, with an action to only fetch a detailed information
    for a few cases at a time"""
    if not roles:
        roles = {}
    if direction == "prev":
        start_idx = max(0, start_idx - num_case_choices())
    else:  # direction == 'next'
        start_idx = min(len(found_cases) - 1, start_idx + num_case_choices())
    # end idx is always as far from start as it can go
    end_idx = min(len(found_cases), start_idx + num_case_choices())
    for case in found_cases[start_idx:end_idx]:
        if not hasattr(case, "title") or not hasattr(case, "date"):
            fetch_case_info(proxy_conn, case, roles=roles)
    return start_idx, end_idx


def any_missing_party_types(
    party_type_map: dict, users: ALPeopleList, other_parties: ALPeopleList
):
    no_missing_required_party_types = True

    def user_has_party_code(p, req_type):
        return hasattr(p, "party_type") and p.party_type == req_type.get("code")

    for p_type in party_type_map.values():
        if p_type.get("isrequired"):
            no_missing_required_party_types &= any(
                filter(lambda p: user_has_party_code(p, p_type), users)
            ) or any(filter(lambda p: user_has_party_code(p, p_type), other_parties))
    return not no_missing_required_party_types


def exactly_one_required_filing_component(fc_opts, fc_map) -> bool:
    if len(fc_opts) > 1 or len(fc_opts) == 0:
        return False
    fc_code = next(iter(fc_opts))[0]
    return fc_map.get(fc_code, {}).get("required")


def matching_tuple_option(option: str, options):
    return next(iter([o for o in options if option in o[1].lower()]), [None])[0]


def fee_total(fee_resp) -> Optional[float]:
    if fee_resp.data:
        val = fee_resp.data.get("feesCalculationAmount", {}).get("value")
        return float(val) if val else None
    return None


def get_full_court_info(proxy_conn, court_id: str) -> Dict:
    """Gets all of the information about the court from the id"""
    full_court_resp = proxy_conn.get_court(court_id)
    if full_court_resp.is_ok():
        return full_court_resp.data
    else:
        log_error_and_notify(
            f"Couldn't get full court info for {court_id}", full_court_resp
        )
        return {}


def _scale_byte_units(value: Union[str, int], unit: str) -> int:
    """Idk if these are right, but there's no examples out there.
    Niem suggests they might not matter:
    https://docs.oasis-open.org/legalxml-courtfiling/ecf/v5.0/csprd03/model/class137602.html
    """
    if isinstance(value, str):
        value = int(value)
    if unit.lower() == "kilobyte" or unit == "kB":
        return value * 1000
    if unit == "KB" or unit == "KiB":
        return value * 1024
    if unit == "MB":
        return value * 1000 * 1000
    return value


def get_max_allowed_sizes(proxy_conn, court_id: str) -> Optional[Tuple[int, int]]:
    """Returns attachment max size, then message max size"""
    policy_resp = proxy_conn.get_policy(court_id)
    if policy_resp.is_ok():
        dev_params = chain_xml(
            policy_resp.data, ["developmentPolicyParameters", "value"]
        )
        attachment_obj = chain_xml(dev_params, ["maximumAllowedAttachmentSize"])
        attachment_max = _scale_byte_units(
            chain_xml(attachment_obj, ["measureValue", "value", "value"]),
            chain_xml(attachment_obj, ["measureUnitText", "value"]),
        )
        message_obj = chain_xml(dev_params, ["maximumAllowedMessageSize"])
        message_max = _scale_byte_units(
            chain_xml(message_obj, ["measureValue", "value", "value"]),
            chain_xml(message_obj, ["measureUnitText", "value"]),
        )
        return attachment_max, message_max
    else:
        return None


class CodeType(str):
    pass


class ContainAny(list):
    pass


# TODO(brycew): python 3.10, make this Iterable[str]
SearchType = Union[Iterable, ContainAny, str, CodeType]


def make_filter(
    search: Union[Callable[..., bool], SearchType, None],
) -> Callable[..., bool]:
    """Makes a 'filter' function from some simple type.

    Necessary because docassemble doesn't store lambdas and functions well in
    interview dicts, so the filters need to be set as primitive types and kept
    that way until the search actually happens (in filter_codes).
    """
    if not search:
        # With None, this is usually with an exclude; so default to False
        return lambda opt: False
    if callable(search):
        return search
    if isinstance(search, CodeType):
        return lambda opt, search_code=search: opt[0] == search_code
    elif isinstance(search, str):
        # unfortunately mypy doesn't work work well with lambdas, so use a def instead
        # https://github.com/python/mypy/issues/4226
        def func_from_str(opt, search_str=search):
            return (opt[1] or "").lower().strip() == search_str.lower().strip()

        return func_from_str
    elif isinstance(search, ContainAny):

        def func_from_any(opt, search_list=search):
            return any(
                [
                    search_item.lower() in (opt[1] or "").lower()
                    for search_item in search_list
                ]
            )

        return func_from_any
    else:  # if isinstance(search, Iterable):

        def func_from_iter(opt, search_list=search):
            return all(
                [
                    search_item.lower() in (opt[1] or "").lower()
                    for search_item in search_list
                ]
            )

        return func_from_iter


def make_filters(
    filters: Iterable[Union[Callable[..., bool], SearchType]],
) -> Iterable[Callable[..., bool]]:
    filter_lambdas = []
    for filter_fn in filters:
        filter_lambdas.append(make_filter(filter_fn))
    for filter_fn in filters:
        if not isinstance(filter_fn, CodeType) and isinstance(filter_fn, str):

            def func_in_str(opt, filter_str=filter_fn):
                return filter_str.lower() in (opt[1] or "").lower()

            filter_lambdas.append(func_in_str)
    return filter_lambdas


def filter_codes(
    options: Iterable,
    filters: Iterable[Union[Callable[..., bool], SearchType]],
    default: str,
    exclude: Union[Callable[..., bool], SearchType, None] = None,
) -> Tuple[List[Any], Optional[str]]:
    """Given a list of filter functions from most specific to least specific,
    (if true, use that code), filters a total list of codes. If any codes match the exclude filter, won't use them.
    """
    codes_tmp: List[Any] = []
    filter_lambdas = make_filters(filters)
    exclude_lambda = make_filter(exclude)
    for filter_fn in filter_lambdas:
        if codes_tmp:
            break
        codes_tmp = [
            opt
            for opt in options
            if filter_fn(opt) and (not exclude or not exclude_lambda(opt))
        ]

    codes = sorted(codes_tmp, key=lambda option: option[1] + str(option[0]))
    if len(codes) == 1:
        return codes, codes[0][0]
    elif len(codes) == 0:
        return list(options), default
    else:
        return codes, None


def check_duplicate_codes(options: List) -> bool:
    if not options or len(options) <= 1:
        return False
    example = options[0]
    for opt in options:
        if isinstance(opt, dict):
            for key, val in opt.values():
                if key != "code" and val != example[key]:
                    return False
        if isinstance(opt, tuple):
            # The first element in the tuple is usually the code itself
            if example[1:] != opt[1:]:
                return False
    return True


def case_labeler(case):
    docket_number = ""
    if hasattr(case, "docket_number"):
        docket_number = case.docket_number
    title = ""
    if hasattr(case, "title"):
        title = case.title
    date = ""
    # Sometimes we get absolutely silly dates on cases. So just don't show anything before year 1000
    if (
        hasattr(case, "date")
        and isinstance(case.date, datetime)
        and case.date.year > 1000
    ):
        date = case.date
    return f"{docket_number} {title} {'(' + date + ')' if date else ''}"


def get_available_efile_courts(proxy_conn) -> list:
    """Gets the list of efilable courts, if it can"""
    resp = proxy_conn.authenticate_user()  # use default config keys
    if resp.response_code == 200:
        court_list = proxy_conn.get_court_list()
        if court_list.is_ok():
            return sorted(court_list.data or [])
        else:
            log_error_and_notify("Couldn't get courts from proxy server?", court_list)
            return []
    else:
        log_error_and_notify("Couldn't login to the proxy server", resp)
        return []
