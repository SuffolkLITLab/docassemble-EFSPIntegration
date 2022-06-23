from typing import Any, Callable, Dict, List, Tuple

from docassemble.base.util import DAObject, DAList, log
from .conversions import parse_case_info, fetch_case_info
from docassemble.AssemblyLine.al_general import ALPeopleList

def num_case_choices() -> int:
  """The number of cases that someone should have to choose between if there are too many.
  Mostly to limit the amount of up-front waiting someone will have to do."""
  return 8

def get_lookup_choices(can_file_non_indexed_case:bool) -> List[Dict[str, str]]:
  lookup_choices = [
    {'party_search': 'Find a case by party name'},
    {'docket_lookup': 'Find a case by case number'},
  ]
  if can_file_non_indexed_case:
    lookup_choices.append({'non_indexed_case': 'I want to file into a non-indexed case'})
  return lookup_choices

def search_case_by_name(*, proxy_conn, var_name:str=None, 
    court_id:str, somebody, filter_fn:Callable[[Any], bool]) -> Tuple[bool, DAList]:
  """Searches for cases by party name. If there are more than 10 cases found, we don't
    add all of the detailed information about the case, just for the first few cases"""
  if not var_name:
    var_name = 'found_cases'
  found_cases = DAList(var_name, object_type=DAObject, auto_gather=False)
  get_cases_response = proxy_conn.get_cases(court_id, person=somebody, docket_id=None)
  cms_connection_issue = get_cases_response.response_code == 203
  if get_cases_response.is_ok():
    # Reversed because cases tend to be returned oldest to newest from Tyler,
    # and people aren't likely to be looking for cases from pre-2000
    for idx, entry in enumerate(reversed(get_cases_response.data)):
      new_case = found_cases.appendObject()
      should_fetch = idx < num_case_choices()
      parse_case_info(proxy_conn, new_case, entry, court_id, fetch=should_fetch, roles={})
      # Allows users to control what cases are shown as options
      if not filter_fn(new_case):
        found_cases.pop()
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
  no_missing_required_party_types_temp = True
  def user_has_party_code(p, req_type):
    return hasattr(p, 'party_type_code') and p.party_type_code == req_type.get('code')
  for p_type in party_type_map.values():
    if p_type.get('isrequired'):
      no_missing_required_party_types_temp &= (
        any(filter(lambda p: user_has_party_code(p, p_type), users)) or
        any(filter(lambda p: user_has_party_code(p, p_type), other_parties))
        )
  return not no_missing_required_party_types_temp

def get_full_court_info(proxy_conn, court_id:str) -> Dict:
  """Gets all of the information about the court from the id"""
  full_court_resp = proxy_conn.get_court(court_id)
  if full_court_resp.is_ok():
    return full_court_resp.data
  else:
    log(f"Couldn't get full court info for {court_id}")
    return {}