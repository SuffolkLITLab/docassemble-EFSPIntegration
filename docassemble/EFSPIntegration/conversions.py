import re
from datetime import datetime
from docassemble.base.util import DADateTime, as_datetime, validation_error
from typing import List, Dict, Tuple, Any, Callable

def convert_court_to_id(trial_court) -> str:
  if isinstance(trial_court, str):
    return trial_court
  return str(trial_court.name)
  
def choices_and_map(codes_list:List, display:str=None, backing:str=None) -> Tuple[List[Any], Dict]:
  if display is None:
    display = '{name}'
  if backing is None:
    backing = 'code'
  choices_list = [(code_obj[backing], display.format(**code_obj)) for code_obj in codes_list]
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

def chain_xml(xml_val, elem_list):
  val = xml_val
  for elem in elem_list:
    if isinstance(val, dict):
      val = val.get(elem, {})
    else:
      val = val[elem]
  return val

def parse_case_info(proxy_conn, new_case, entry, court_id):
  new_case.details = entry
  new_case.court_id = court_id
  new_case.tracking_id =  chain_xml(entry, ['value', 'caseTrackingID', 'value'])
  new_case.docket_id = entry.get('value',{}).get('caseDocketID',{}).get('value')
  new_case.category = entry.get('value',{}).get('caseCategoryText',{}).get('value')
       
  new_case.case_details = proxy_conn.get_case(court_id, new_case.tracking_id).data
  # TODO: is the order of this array predictable? might it break if Tyler changes something?        
  new_case.case_type = new_case.case_details.get('value').get('rest',[{},{}])[1].get('value',{}).get('caseTypeText',{}).get('value')
  new_case.title = new_case.case_details.get('value',{}).get('caseTitleText',{}).get('value')        
  new_case.date = as_datetime(datetime.utcfromtimestamp(new_case.case_details.get('value',{}).get('activityDateRepresentation',{}).get('value',{}).get('dateRepresentation',{}).get('value',{}).get('value',1000)/1000))
  
def case_xml_to_parties(case_xml):
  rest_list = chain_xml(case_xml, ['value', 'rest'])
  tyler_aug = [aug for aug in rest_list if 'tyler.ecf' in aug.get('declaredType')][0]
  return chain_xml(tyler_aug, ['value', 'caseParticipant'])

def parties_xml_to_choices(parties_xml):
  choices = []
  for party in parties_xml:
    entity = chain_xml(party, ['value', 'entityRepresentation', 'value'])
    name = entity.get('personName', {})
    full_name = f"{name.get('personGivenName', {}).get('value','')} {name.get('personMiddleName', {}).get('value','')} {name.get('personSurName',{}).get('value','')}"
    per_id = chain_xml(entity, ['personOtherIdentification', 0, 'identificationID', 'value'])
    choices.append((per_id, name))
  return choices

def filter_payment_accounts(account_list, allowable_card_types):
  """ Gets a list of all payment accounts and filters them by if the card is 
      accepted at a particular court"""
  not_card_or_allowed_card = lambda acct: acct.get('paymentAccountTypeCode') != 'CC' or \
      (acct.get('paymentAccountTypeCode') == 'CC' and acct.get('cardType',{}).get('value') in allowable_card_types)
  def display(acct):
    if acct.get('paymentAccountTypeCode') == 'CC':
      return f"{acct.get('accountName')} ({acct.get('cardType',{}).get('value')})"
    elif acct.get('paymentAccountTypeCode') == 'WV':
      return f"{acct.get('accountName')} (Waiver account)"
    else:
      return f"{acct.get('accountName')} ({acct.get('paymentAccountTypeCode')})"
  return [(account.get('paymentAccountID'), display(account)) 
        for account in account_list if account.get('active',{}).get('value') and not_card_or_allowed_card(account)]