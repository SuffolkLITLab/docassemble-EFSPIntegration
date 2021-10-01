import re
from datetime import datetime
from docassemble.base.util import DADateTime, as_datetime, validation_error
from typing import List, Dict, Tuple, Any, Callable

def convert_court_to_id(trial_court) -> str:
  # TODO(brycew): actually implement
  if isinstance(trial_court, str):
    return trial_court.lower()
  return str(trial_court.name).lower()
  
def choices_and_map(codes_list:List, display:str=None, backing:str=None) -> Tuple[List[Any], Dict]:
  if display is None:
    display = '{name}'
  if backing is None:
    backing = 'code'
  choices_list = list(map(lambda vv: (vv[backing], display.format(**vv)), codes_list))
  codes_map = { vv[backing] : vv for vv in codes_list }
  return choices_list, codes_map

def pretty_display(data, tab_depth=0):
  tab_inc = 4
  out = ''
  if isinstance(data, list):
    for idx, elem in enumerate(data):
      out += (' ' * tab_depth) + f'* idx: {idx}\n'
      out += pretty_display(elem, tab_depth + tab_inc)

  elif isinstance(data, dict):
    for key, val in data.items():
      if val is not None and val != []:
        out += (' ' * tab_depth) + f'* {key}: \n'
        out += pretty_display(val, tab_depth + tab_inc)
  else:
    out = (' ' * tab_depth) + str(data) + '\n'
  return out

def tyler_timestamp_to_datetime(tyler_timestamp:int)->DADateTime:
  return as_datetime(datetime.utcfromtimestamp(tyler_timestamp/1000))

def validate_tyler_regex(dataField:Dict)->Callable:
  """
  Return a function that validates a given input with the provided regex,
  suitable for use with Docassemble's `validate:` question modifier
  """
  def fn_validate(input):
    if not dataField:
      return True # Don't want to stop on-screen validation if we can't retrieve the code
    if re.match(dataField.get('regularexpression'), str(input)):
      return True
    validation_message = dataField.get('validationmessage')
    if not validation_message:
      validation_message =  'Enter a valid value'
      # Hardcode the fallback validation message for 1-999. Inexplicably, no validation message
      # supplied for 1-999 in Illinois but I think this will stay the same for a long time
      if dataField.get('regularexpression') == r'^([1-9][0-9]{0,2})$':
        validation_message = "Enter a number betweeen 1-999"
      elif dataField.get('regularexpression') == r'^([0-9]{0,9}(\.([0-9]{0,2}))?)$':
        validation_message = "Enter a number between 0-999,999,999"
      elif dataField.get('regularexpression') == r'^[0-9]*$':
        validation_message = "Enter only digits"
    validation_error(validation_message)
  return fn_validate

def is_person(possible_person:dict):
  """Helper for getting party ID"""
  return not possible_person.get('value',{}).get('entityRepresentation',{}).get('value',{}).get('personOtherIdentification') is None

def get_person_name_and_id(party:dict):
  """Helper for getting party ID"""  
  person_name = party.get('value',{}).get('entityRepresentation',{}).get('value',{}).get('personName',{})
  person_name_str = f"{person_name.get('personGivenName',{}).get('value','')} {person_name.get('personMiddleName',{}).get('value','')} {person_name.get('personSurName',{}).get('value','')}"
  person = party.get('value',{}).get('entityRepresentation',{}).get('value',{}).get('personOtherIdentification')
  first_rep = next(iter(person),{})
  return {first_rep.get('identificationID',{}).get('value'): person_name_str}
