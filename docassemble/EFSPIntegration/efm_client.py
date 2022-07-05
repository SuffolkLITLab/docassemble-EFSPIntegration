#!/usr/bin/env python3
import json
import pycountry
from typing import Union, Dict

import requests
from docassemble.base.functions import all_variables, get_config
from docassemble.base.util import DAObject, log, Person, Individual, DADateTime, as_datetime, reconsider
from docassemble.AssemblyLine.al_document import ALDocumentBundle
from docassemble.AssemblyLine.al_general import ALIndividual
from .py_efsp_client import ApiResponse, EfspConnection, _user_visible_resp

__all__ = ['ApiResponse','ProxyConnection', 'state_name_to_code']

def state_name_to_code(state_name:str) -> str:
  try:
    return pycountry.subdivisions.lookup(state_name).code.split('-')[-1]
  except LookupError as ex:
    return state_name

def _give_data_url(bundle: ALDocumentBundle):
  """Prepares the filing documents by setting a semi-permanent enabled and a data url
  The document bundle can either consist of documents or other document bundles. But each top element will
  sent to Tyler as a separate filing document, and needs to have the necessary attributes set (tyler_filing_id, etc)
  """
  if bundle is None:
    return
  for doc in bundle:
    doc.proxy_enabled = doc.always_enabled or doc.enabled
    if doc.proxy_enabled:
      doc.data_url = doc.as_pdf().url_for(external=True, temporary=True)
      doc.page_count = doc.as_pdf().num_pages()
    if hasattr(doc, 'enabled'):
      del doc.enabled

def _get_all_vars(bundle: ALDocumentBundle):
  """Strips out some extra big variables that we don't need to serialize and send across the network"""
  _give_data_url(bundle)
  all_vars_dict = all_variables()
  vars_to_pop = ['trial_court_resp', 'x', 'trial_court_options', 'found_case', 'selected_existing_case', 
      'filing_type_options', 'filing_type_map', 'party_type_options',
      'available_efile_courts', 'case_category_map', 'full_court_info', 'tyler_login_resp', 'case_type_map', 'all_courts', 
      'al_user_bundle', 'court_emails', 'party_type_map']
  for var in vars_to_pop:
    all_vars_dict.pop(var, None)

  for doc in all_vars_dict.get('al_court_bundle', {}).get('elements', []):
    doc.pop('optional_service_options', None)
    doc.pop('optional_service_map', None)
    
  return json.dumps(all_vars_dict)

class ProxyConnection(EfspConnection):
  def __init__(self, *, url:str=None, api_key:str=None, credentials_code_block:str='tyler_login', default_jurisdiction:str=None):
    """
    Params:
      url (str)
      api_key (str)
      credentials_code_block (str)
      default_jurisdiction (str)
    """
    temp_efile_config = get_config('efile proxy', {})
    if url is None:
      url = temp_efile_config.get('url', '')
    if api_key is None:
      api_key = temp_efile_config.get('api key')

    self.credentials_code_block = credentials_code_block

    def internal_call_proxy(conn, send_func) -> ApiResponse:
      try:
        resp = send_func()
        if resp.status_code == 401 and conn.credentials_code_block:
          reconsider(conn.credentials_code_block)
      except requests.ConnectionError as ex:
        return _user_visible_resp(f'Could not connect to the Proxy server at {conn.base_url}: {ex}')
      except requests.exceptions.MissingSchema as ex:
        return _user_visible_resp(f'Url {conn.base_url} is not valid: {ex}')
      return _user_visible_resp(resp)

    super().__init__(url=url, api_key=api_key, default_jurisdiction=default_jurisdiction, call_proxy=internal_call_proxy)

  def authenticate_user(self, tyler_email:str=None, tyler_password:str=None, jeffnet_key:str=None, *, jurisdiction:str=None):
    """
    Params:
        tyler_email (str)
        tyler_password (str)
        jeffnet_key (str)
    """
    temp_efile_config = get_config('efile proxy', {})
    if tyler_email is None:
      tyler_email = temp_efile_config.get('tyler email')
    if tyler_password is None:
      tyler_password = temp_efile_config.get('tyler password')
    if jeffnet_key is None:
      jeffnet_key = temp_efile_config.get('jeffnet api token')
    return super().authenticate_user(tyler_email=tyler_email,
        tyler_password=tyler_password,
        jeffnet_key=jeffnet_key,
        jurisdiction=jurisdiction)

  def register_user(self, person:Union[Individual, dict], registration_type:str, *, password:str=None, firm_name_or_id:str=None):
    """
    registration_type needs to be INDIVIDUAL, FIRM_ADMINISTRATOR, or FIRM_ADMIN_NEW_MEMBER.
    If registration_type is INDIVIDUAL or FIRM_ADMINISTRATOR, you need a password.
    If it's FIRM_ADMINISTRATOR or FIRM_ADMIN_NEW_MEMBER, you need a firm_name_or_id
    """
    if isinstance(person, Individual):
      person = person.as_serializable()
    return super().register_user(person, registration_type, password=password, firm_name_or_id=firm_name_or_id)

  #### Managing Firm Users

  def update_firm(self, firm:Person):
    # firm is stateful
    update = serialize_person(firm)
    return super().update_firm(update)

  # Managing Service Contacts
  def update_service_contact(self, service_contact_id:str, service_contact:Individual, is_public:bool=None, is_in_master_list:bool=None, admin_copy:str=None):
    service_contact_dict = serialize_person(service_contact)
    return super().update_service_contact(service_contact_id, service_contact_dict, is_public=is_public, is_in_master_list=is_in_master_list, admin_copy=admin_copy)

  def create_service_contact(self, service_contact:Individual, *, is_public:bool, is_in_master_list:bool, admin_copy:str=None):
    service_contact_dict = serialize_person(service_contact)
    return super().create_service_contact(service_contact_dict, is_public=is_public, is_in_master_list=is_in_master_list, admin_copy=admin_copy)

  def check_filing(self, court_id:str, court_bundle:ALDocumentBundle):
    all_vars = _get_all_vars(court_bundle)
    return super().check_filing(court_id, all_vars)

  def file_for_review(self, court_id:str, court_bundle:ALDocumentBundle):
    all_vars = _get_all_vars(court_bundle)
    return super().file_for_review(court_id, all_vars)

  def get_service_types(self, court_id:str, court_bundle:ALDocumentBundle=None):
    """Checks the court info: if it has conditional service types, call a special API with all filing info so far to get service types"""
    court_info = self.get_court(court_id)
    if court_info.data.get('hasconditionalservicetypes') and court_bundle:
      all_vars = _get_all_vars(court_bundle)
    else:
      all_vars = {}
    return super().get_service_types(court_id, all_vars=all_vars)

  def calculate_filing_fees(self, court_id:str, court_bundle:ALDocumentBundle):
    all_vars = _get_all_vars(court_bundle)
    return super().calculate_filing_fees(court_id, all_vars)

  def get_return_date(self, court_id:str, req_return_date, court_bundle:ALDocumentBundle):
    all_vars_obj = _get_all_vars(court_bundle)
    return super().get_return_date(court_id, req_return_date, all_vars_obj)

  def get_cases(self, court_id:str, *, person:ALIndividual=None, docket_id:str=None):
    if person is None:
      return super().get_cases_raw(court_id, docket_id=docket_id)
    if person.person_type == 'business':
      return super().get_cases_raw(court_id, business_name=person.name.first, docket_id=docket_id)
    else:
      return super().get_cases_raw(court_id, person_name=person.name.as_serializable(), docket_id=docket_id)

def serialize_person(person:Union[Person,Individual])->Dict:
  """
  Converts a Docassemble Person or Individual into a dictionary suitable for
  json.dumps and in format expected by Tyler-specific endpoints on the EFSPProxy
  """
  if isinstance(person, Individual):
    return_dict = {
      "firstName": person.name.first,
      "middleName": person.name.middle if hasattr(person.name, 'middle') else None,
      "lastName": person.name.last,
    }
  else:
    return_dict = {
      "firmName": person.name.text if hasattr(person.name, 'text') else None,
    }
  return_dict.update({
    "address": {
      "addressLine1": person.address.address if hasattr(person.address, 'address') else None,
      "addressLine2": person.address.unit if hasattr(person.address, 'unit') else None,
      "city": person.address.city if hasattr(person.address, 'city') else None,
      "state": person.address.state if hasattr(person.address, 'state') else None,
      "zipCode": person.address.zip if hasattr(person.address, 'zip') else None,
      "country": person.address.country if hasattr(person.address, 'country') else 'US',
    },
    "phoneNumber": person.phone_number if hasattr(person, 'phone_number') else None,
    "email": person.email if hasattr(person, 'email') else ''
  })

  return return_dict
