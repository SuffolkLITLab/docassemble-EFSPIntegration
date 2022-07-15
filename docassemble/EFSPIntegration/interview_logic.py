"""
A group of methods that were code blocks in various parts of the EFSP
package, but for better python tooling support, were moved here.
"""

from typing import Any, Callable, Dict, List, Tuple, Optional, Iterable, Union

from docassemble.base.util import DAObject, DAList, log
from docassemble.base.functions import safe_json
from .conversions import parse_case_info, fetch_case_info, transform_json_variables
from docassemble.AssemblyLine.al_general import ALPeopleList

class EFCaseSearch(DAObject):
  court_id:str
  can_file_non_indexed_case: bool
  do_what_choice: str
  found_case: DAObject
  case_was_found: bool

def num_case_choices() -> int:
  """The number of cases that someone should have to choose between if there are too many.
  Mostly to limit the amount of up-front waiting someone will have to do."""
  return 8

def get_lookup_choices(can_file_non_indexed_case:bool) -> List[Dict[str, str]]:
  lookup_choices = [
    {'party_search': 'Party name'},
    {'docket_lookup': 'Case number'},
  ]
  if can_file_non_indexed_case:
    lookup_choices.append({'non_indexed_case': 'I want to file into a non-indexed case'})
  return lookup_choices

def json_wrap(item:Tuple):
  return safe_json([*item])

def json_unwrap(val):
  return transform_json_variables(val)

def search_case_by_name(*, proxy_conn, var_name:str=None, 
    court_id:str, somebody, filter_fn:Callable[[Any], bool], roles=None) -> Tuple[bool, DAList]:
  """Searches for cases by party name. If there are more than 10 cases found, we don't
    add all of the detailed information about the case, just for the first few cases"""
  if not var_name:
    var_name = 'found_cases'
  found_cases = DAList(var_name, object_type=DAObject, auto_gather=False)
  get_cases_response = proxy_conn.get_cases(court_id, person=somebody, docket_number=None)
  cms_connection_issue = get_cases_response.response_code == 203
  if get_cases_response.is_ok():
    found_cases.resp_ok = True
    # Reversed because cases tend to be returned oldest to newest from Tyler,
    # and people aren't likely to be looking for cases from pre-2000
    for idx, entry in enumerate(reversed(get_cases_response.data)):
      new_case = found_cases.appendObject()
      should_fetch = idx < num_case_choices()
      parse_case_info(proxy_conn, new_case, entry, court_id, fetch=should_fetch, roles=roles)
      # Allows users to control what cases are shown as options
      if not filter_fn(new_case):
        found_cases.pop()
  else:
    found_cases.resp_ok = False
  found_cases.gathered = True
  return cms_connection_issue, found_cases

def shift_case_select_window(proxy_conn, found_cases:DAList, *, 
    direction:str, start_idx:int, end_idx:int) -> Tuple[int, int]:
  """Specifically used in case_search.yml, with an action to only fetch a detailed information
  for a few cases at a time"""
  if direction == 'prev':
    start_idx = max(0, start_idx - num_case_choices())
  else: # direction == 'next'
    start_idx = min(len(found_cases) - 1, start_idx + num_case_choices())
  # end idx is always as far from start as it can go
  end_idx = min(len(found_cases), start_idx + num_case_choices())
  for case in found_cases[start_idx:end_idx]:
    if not hasattr(case, 'title'):
      fetch_case_info(proxy_conn, case, roles={})
  return start_idx, end_idx

def any_missing_party_types(party_type_map:dict, users:ALPeopleList, other_parties:ALPeopleList):
  no_missing_required_party_types = True
  def user_has_party_code(p, req_type):
    return hasattr(p, 'party_type') and p.party_type == req_type.get('code')
  for p_type in party_type_map.values():
    if p_type.get('isrequired'):
      no_missing_required_party_types &= (
        any(filter(lambda p: user_has_party_code(p, p_type), users)) or
        any(filter(lambda p: user_has_party_code(p, p_type), other_parties))
        )
  return not no_missing_required_party_types

def exactly_one_required_filing_component(fc_opts, fc_map) -> bool:
  if len(fc_opts) > 1 or len(fc_opts) == 0:
    return False
  fc_code = next(iter(fc_opts))[0]
  return fc_map.get(fc_code,{}).get('required')

def matching_tuple_option(option:str, options):
  return next(iter([o for o in options if option in o[1].lower()]),[None])[0]

def fee_total(fee_resp) -> str:
  if fee_resp.data:
    return fee_resp.data.get('feesCalculationAmount',{}).get('value', 'N/A')
  return 'N/A'

def get_full_court_info(proxy_conn, court_id:str) -> Dict:
  """Gets all of the information about the court from the id"""
  full_court_resp = proxy_conn.get_court(court_id)
  if full_court_resp.is_ok():
    return full_court_resp.data
  else:
    log(f"Couldn't get full court info for {court_id}")
    return {}

def filter_codes(options, filters:Iterable[Union[Callable[..., bool], str]], default:str) -> Tuple[List[Any], Optional[str]]:
  """Given a list of filter functions from most specific to least specific,
  (if true, use that code)
  filters a total list of codes"""
  codes_tmp: List[Any] = []
  for filter_fn in filters:
    if codes_tmp:
      break
    if isinstance(filter_fn, str):
      match_this = filter_fn
      filter_fn = lambda opt: opt[1].lower() == match_this.lower()
    codes_tmp = [opt for opt in options if filter_fn(opt)]
  if not codes_tmp:
    for filter_st in filters:
      if codes_tmp:
        break
      if isinstance(filter_st, str):
        contain_this = filter_st
        filter_fn = lambda opt: contain_this.lower() in opt[1].lower()
        codes_tmp = [opt for opt in options if filter_fn(opt)]

  codes = sorted(codes_tmp, key=lambda option: option[1])
  if len(codes) == 1:
    return codes, codes[0][0]
  elif len(codes) == 0:
    return options, default
  else:
    return codes, None

def case_labeler(case):
  docket_number = ''
  if hasattr(case, 'docket_number'):
    docket_number = case.docket_number
  title = ''
  if hasattr(case, 'title'):
    title = case.title
  date = ''
  if hasattr(case, 'date'):
    date = case.date
  return f"{docket_number} {title} ({date})"

def get_available_efile_courts(proxy_conn):
  """Gets the list of efilable courts, if it can"""
  resp = proxy_conn.authenticate_user() # use default config keys
  if resp.response_code == 200:
    court_list = proxy_conn.get_court_list()
    if court_list.is_ok():
      return sorted(court_list.data or [])
    else:
      log(f"Couldn't get courts from proxy server? {court_list}")
      return []
  else:
    log(f"Couldn't login to the proxy server!: {resp}")
    return []
