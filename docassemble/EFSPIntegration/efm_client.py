#!/usr/bin/env python3
import re
import json
import logging
from typing import List
import http.client as http_client

from urllib.parse import urlencode
import requests
from docassemble.base.functions import all_variables, get_config
from docassemble.base.util import IndividualName, DAObject, log
from docassemble.AssemblyLine.al_document import ALDocumentBundle

__all__ = ['ApiResponse','ProxyConnection']

class ApiResponse(DAObject):
  def __init__(self, response_code, error_msg:str, data):
    self.response_code = response_code
    self.error_msg = error_msg
    self.data = data

  def __str__(self):
    if self.error_msg:
      return f'response_code: {self.response_code}, error_msg: {self.error_msg}, data: {self.data}'
    return f'response_code: {self.response_code}, data: {self.data}'

  def __repr__(self):
    return str(self)

  def is_ok(self):
    return self.response_code in [200, 201, 202, 203, 204, 205]

def _recursive_give_data_url(bundle):
  """Prepares the document types by setting a semi-permanent enabled and a data url"""
  for doc in bundle:
    if isinstance(doc, ALDocumentBundle):
      _recursive_give_data_url(doc)
    else:
      doc.proxy_enabled = doc.always_enabled or doc.enabled
      if doc.proxy_enabled:
        doc.data_url = doc.as_pdf().url_for(temporary=True)
      if hasattr(doc, 'enabled'):
        del doc.enabled

class ProxyConnection:
  def __init__(self, url:str=None, api_key:str=None):
    temp_efile_config = get_config('efile proxy', {})
    if url is None:
      url = temp_efile_config.get('url')
    if api_key is None:
      api_key = temp_efile_config.get('api key')

    if not url.endswith('/'):
      url = url + '/'
    self.base_url = url
    self.api_key = api_key
    self.proxy_client = requests.Session()
    self.active_token = None
    self.proxy_client.headers = {
      'Content-type': 'application/json',
      'Accept': 'application/json',
    }
    self.proxy_client.headers['X-API-KEY'] = api_key 
    self.verbose = False
    self.authed_user_id = None
    self.set_verbose_logging(True)

  def _call_proxy(self, send_func):
    try:
      resp = send_func()
      if resp.status_code == 401:
        auth_resp = self.authenticate_user()
        if auth_resp.response_code == 200:
          resp = send_func()
    except requests.ConnectionError as ex:
      return ProxyConnection.user_visible_resp(f'Could not connect to the Proxy server at {self.base_url}: {ex}')
    return ProxyConnection.user_visible_resp(resp)

  @staticmethod
  # TODO(brycew): this is old zeep logging: update to use requests
  def verbose_logging(turn_on: bool):
    if turn_on:
      http_client.HTTPConnection.debuglevel = 1
      logging.basicConfig()
      logging.getLogger().setLevel(logging.DEBUG)
      requests_log = logging.getLogger("requests.packages.urllib3")
      requests_log.setLevel(logging.DEBUG)
      requests_log.propagate = True

  def set_verbose_logging(self, turn_on: bool):
    if self.verbose != turn_on:
      ProxyConnection.verbose_logging(turn_on)
    self.verbose = turn_on

  @staticmethod
  def user_visible_resp(resp):
    """By default, the responses from `requests` aren't pickable, which causes
        some issues in Docassemble if you are using this in interviews. This function
        takes the essentials of a response and puts in into a simple object.
    """
    if resp is None:
      return ApiResponse(501, 'Not yet implemented (on both sides)', None)
    # Something went wrong with us / some error in requests
    if isinstance(resp, str):
      return ApiResponse(-1, resp, None)
    try:
      data = resp.json()
      return ApiResponse(resp.status_code, None, data)
    except:
      return ApiResponse(resp.status_code, resp.text, None)

  def authenticate_user(self, tyler_email:str=None, tyler_password:str=None, jeffnet_key:str=None):
    temp_efile_config = get_config('efile proxy', {})
    if tyler_email is None:
      tyler_email = temp_efile_config.get('tyler email')
    if tyler_password is None:
      tyler_password = temp_efile_config.get('tyler password')
    if jeffnet_key is None:
      jeffnet_key = temp_efile_config.get('jeffnet api token')
    auth_obj = {}
    auth_obj['api_key'] = self.api_key
    if jeffnet_key:
      auth_obj['jeffnet'] = {'key': jeffnet_key}
    if tyler_email and tyler_password:
      auth_obj['tyler'] = {'username': tyler_email, 'password': tyler_password}
    try:
      resp = self.proxy_client.post(self.base_url + 'adminusers/authenticate', 
        data=json.dumps(auth_obj))
      if resp.status_code == requests.codes.ok:
        all_tokens = resp.json()
        for k, v in all_tokens.items():
          self.proxy_client.headers[k] = v
        # self.authed_user_id = data['userID']
    except requests.ConnectionError as ex:
      return ProxyConnection.user_visible_resp(
        f'Could not connect to the Proxy server at {self.base_url}')
    return ProxyConnection.user_visible_resp(resp)

  def register_user(self, person, registration_type:str, password:str=None, firm_name_or_id:str=None):
    """
    registration_type needs to be INDIVIDUAL, FIRM_ADMINISTRATOR, or FIRM_ADMIN_NEW_MEMBER. 
    If registration_type is INDIVIDUAL or FIRM_ADMINISTRATOR, you need a password. 
    If it's FIRM_ADMINISTRATOR or FIRM_ADMIN_NEW_MEMBER, you need a firm_name_or_id
    """
    if hasattr(person, 'phone_number'):
      phone_number = person.phone_number
    elif hasattr(person, 'mobile_number'):
      phone_number = person.mobile_number
    else:
      phone_number = ''
    reg_obj = {
          'registrationType': registration_type.upper(),
          'email': person.email,
          'firstName': person.name.first,
          'middleName': person.name.middle,
          'lastName': person.name.last,
          'streetAddressLine1': person.address.address,
          'streetAddressLine2': person.address.unit,
          'city': person.address.city,
          'stateCode': person.address.state,
          'zipCode': person.address.zip,
          'countryCode': person.address.country,
          'phoneNumber': phone_number
    }
    if registration_type != 'INDIVIDUAL':
      reg_obj['firmName'] = firm_name_or_id
    if registration_type != 'FIRM_ADMIN_NEW_MEMBER':
      reg_obj['password'] = password

    send = lambda: self.proxy_client.put(self.base_url + 'adminusers/users', data=json.dumps(reg_obj))
    return self._call_proxy(send)

  def get_password_rules(self):
    """
    Password rules are stored in the global court, id 1.
    """
    send = lambda: self.proxy_client.get(self.base_url + "/codes/courts/1/datafields/GlobalPassword")
    return self._call_proxy(send)

  def is_valid_password(self, password):
    results = self.get_password_rules()
    if not results.data:
      log(str(results))
    try:
      return bool(re.match(results.data.get('regularexpression'), password))
    except:
      return None      

  # Managing Firm Users

  def get_user_list(self):
    send = lambda: self.proxy_client.get(self.base_url + 'adminusers/users')
    return self._call_proxy(send)

  def get_users(self):
    return self.get_user_list()

  def get_user(self, id:str=None):
    if id is None:
      send = lambda: self.proxy_client.get(self.base_url + f'adminusers/user')
    else:
      send = lambda: self.proxy_client.get(self.base_url + f'adminusers/users/{id}')
    return self._call_proxy(send)

  def get_user_roles(self, id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'adminusers/users/{id}/roles')
    return self._call_proxy(send) 

  def add_user_roles(self, id:str, roles:List[dict]):
    send = lambda: self.proxy_client.post(self.base_url + f'adminusers/users/{id}/roles', 
      data=json.dumps(roles))
    return self._call_proxy(send) 

  def remove_user_roles(self, id:str, roles:List[dict]):
    send = lambda: self.proxy_client.delete(self.base_url + f'adminusers/users/{id}/roles',
        data=json.dumps(roles))
    return self._call_proxy(send) 

  def change_password(self, id:str, email:str, new_password:str): 
    send = lambda: self.proxy_client.post(self.base_url + f'adminusers/users/{id}/password',
        data=json.dumps({'email': email, 'newPassword': new_password}))
    return self._call_proxy(send) 

  def self_change_password(self, current_password:str, new_password:str):
    send = lambda: self.proxy_client.post(self.base_url + f'adminusers/user/password',
        data=json.dumps({'currentPassword': current_password, 'newPassword': new_password}))
    return self._call_proxy(send) 

  def self_resend_activation_email(self, email: str):
    send = lambda: self.proxy_client.post(self.base_url + 'adminusers/user/resend-activation-email',
        data=email)
    return self._call_proxy(send)

  def resend_activation_email(self, id:str):
    send = lambda: self.proxy_client.post(self.base_url + f'adminusers/users/{id}/resend-activation-email')
    return self._call_proxy(send) 

  def update_notification_preferences(self, notif_preferences:List[dict]):
    send = lambda: self.proxy_client.patch(self.base_url + f'adminusers/user/notification-preferences', 
        data=json.dumps(notif_preferences))
    return self._call_proxy(send)

  def get_notification_preferences(self):
    send = lambda: self.proxy_client.get(self.base_url + 'adminusers/user/notification-preferences')
    return self._call_proxy(send)

  def get_notification_options(self):
    """AKA NotificationPreferencesList"""
    send = lambda: self.proxy_client.get(self.base_url + 'adminusers/notification-options')
    return self._call_proxy(send)

  def update_user(self, id:str, email:str=None, first_name:str=None, middle_name:str=None, last_name:str=None):
    updated_user = {'email': email, 'firstName': first_name, 'middleName': middle_name, 'lastName': last_name}
    send = lambda: self.proxy_client.patch(self.base_url + f'adminusers/users/{id}', data=json.dumps(updated_user))
    return self._call_proxy(send) 

  def remove_user(self, id:str):
    #if id is None:
    #    id = self.authed_user_id
    send = lambda: self.proxy_client.delete(self.base_url + f'adminusers/users/{id}')
    return self._call_proxy(send)

  # TODO(brycew): not tested
  def reset_user_password(self, email:str):
    send = lambda: self.proxy_client.post(self.base_url + 'adminusers/user/password/reset', data=email)
    return self._call_proxy(send)

  def get_password_question(self, email:str):
    send = lambda: self.proxy_client.get(self.base_url + 'adminusers/user/password-question', data=email)
    return self._call_proxy(send)

  # Managing a Firm
  def get_firm(self):
    send = lambda: self.proxy_client.get(self.base_url + 'firmattorneyservice/firm')
    return self._call_proxy(send)

  def update_firm(self, **kwargs):
    send = lambda: self.proxy_client.patch(self.base_url + f'firmattorneyservice/firm', data=json.dumps(kwargs))
    return self._call_proxy(send) 

  # Managing Attorneys
  def get_attorney_list(self):
    send = lambda: self.proxy_client.get(self.base_url + f'firmattorneyservice/attorneys')
    return self._call_proxy(send) 

  def get_attorney(self, attorney_id):
    send = lambda: self.proxy_client.get(self.base_url + f'firmattorneyservice/attorneys/{attorney_id}')
    return self._call_proxy(send)

  def update_attorney(self, attorney_id, bar_number:str=None, 
      first_name:str=None, middle_name:str=None, last_name:str=None):
    send = lambda: self.proxy_client.patch(self.base_url + f'firmattorneyservice/attorneys/{attorney_id}', 
        data=json.dumps({'barNumber': bar_number, 'firstName': first_name, 'middleName': middle_name, 'lastName': last_name}))
    return self._call_proxy(send) 

  def create_attorney(self, bar_number:str, first_name:str, middle_name:str=None, last_name:str=None):
    send = lambda: self.proxy_client.post(self.base_url + f'firmattorneyservice/attorneys', 
        data=json.dumps({'barNumber': bar_number, 'firstName': first_name, 'middleName': middle_name, 'lastName': last_name}))
    return self._call_proxy(send) 

  def remove_attorney(self, attorney_id):
    send = lambda: self.proxy_client.delete(self.base_url + f'firmattorneyservice/attorneys/{attorney_id}')
    return self._call_proxy(send) 

  # Managing Payment Accounts
  def get_payment_account_type_list(self):
    send = lambda: self.proxy_client.get(self.base_url + f'payments/types')
    return self._call_proxy(send) 

  def get_payment_account_list(self):
    send = lambda: self.proxy_client.get(self.base_url + f'payments/payment-accounts')
    return self._call_proxy(send) 

  def get_payment_account(self, payment_account_id):
    send = lambda: self.proxy_client.get(self.base_url + f'payments/payment-accounts/{payment_account_id}')
    return self._call_proxy(send)

  def update_payment_account(self, payment_account_id, account_name:str=None, active:bool=True):
    send = lambda: self.proxy_client.patch(self.base_url + f'payments/payment-accounts/{payment_account_id}', 
        data=json.dumps({'account_name': account_name, 'active': active}))
    return self._call_proxy(send) 

  def create_payment_account(self, **kwargs):
    send = lambda: self.proxy_client.post(self.base_url + f'payments/payment-accounts', data=json.dumps(kwargs))
    return self._call_proxy(send) 

  def remove_payment_account(self, payment_account_id):
    send = lambda: self.proxy_client.delete(self.base_url + f'payments/payment-accounts/{payment_account_id}')
    return self._call_proxy(send) 

  # Global Payment Accounts
  def get_global_payment_account_list(self):
    send = lambda: self.proxy_client.get(self.base_url + f'payments/global-accounts')
    return self._call_proxy(send) 

  def get_global_payment_account(self, global_payment_account_id):
    send = lambda: self.proxy_client.get(self.base_url + f'payments/global-accounts/{global_payment_account_id}')
    return self._call_proxy(send) 

  def update_global_payment_account(self, global_payment_account_id, account_name:str=None, active:bool=True):
    send = lambda: self.proxy_client.patch(self.base_url + f'payments/global-accounts/{global_payment_account_id}', 
        data=json.dumps({'account_name': account_name, 'active': active}))
    return self._call_proxy(send) 

  def create_global_payment_account(self, **kwargs):
    send = lambda: self.proxy_client.post(self.base_url + f'payments/global-accounts', data=json.dumps(kwargs))
    return self._call_proxy(send) 

  def remove_global_payment_account(self, global_payment_account_id):
    send = lambda: self.proxy_client.delete(self.base_url + f'payments/global-accounts/{global_payment_account_id}')
    return self._call_proxy(send) 

  # Managing Service Contacts
  # Service contacts are part of the `firm` hierarchy
  def get_service_contact_list(self):
    send = lambda: self.proxy_client.get(self.base_url + f'firmattorneyservice/service-contacts')
    return self._call_proxy(send)

  def get_service_contact(self, service_contact_id):
    send = lambda: self.proxy_client.get(self.base_url + f'firmattorneyservice/service-contacts/{service_contact_id}')
    return self._call_proxy(send)

  def update_service_contact(self, service_contact_id, **kwargs):
    send = lambda: self.proxy_client.patch(self.base_url + f'firmattorneyservice/service-contacts/{service_contact_id}', 
        data=json.dumps(kwargs))
    return self._call_proxy(send)

  def create_service_contact(self, service_contact):
    send = lambda: self.proxy_client.post(self.base_url + f'firmattorneyservice/service-contacts', 
        data=json.dumps(service_contact))
    return self._call_proxy(send)

  def remove_service_contact(self, service_contact_id):
    send = lambda: self.proxy_client.delete(self.base_url + f'firmattorneyservice/service-contacts/{service_contact_id}')
    return self._call_proxy(send)

  def get_public_service_contacts(self, first_name:str=None, middle_name:str=None, last_name:str=None, email:str=None):
    send = lambda: self.proxy_client.get(self.base_url + f'firmattorneyservice/service-contacts/public',
        data=json.dumps({'firstName': first_name, 'middleName': middle_name, 'lastName': last_name, 'email': email}))
    return self._call_proxy(send)

  # Using Service Contacts
  def attach_service_contact(self, service_contact_id:str, case_id:str, case_party_id:str=None):
    send = lambda: self.proxy_client.put(self.base_url + f'firmattorneyservice/service-contacts/{service_contact_id}/cases',
        data=json.dumps({'caseId': case_id, 'casepartyId': case_party_id}))
    return self._call_proxy(send)

  def detach_service_contact(self, service_contact_id:str, case_id:str, case_party_id:str=None):
    url = self.base_url + f'firmattorneyservice/service-contacts/{service_contact_id}/cases/{case_id}'
    if case_party_id is not None:
      url += urlencode({'case_party_id': case_party_id})
    send = lambda: self.proxy_client.delete(url)
    return self._call_proxy(send)

  def get_public_list(self):
    send = lambda: self.proxy_client.get(self.base_url + f'firmattorneyservice/public-service-contacts')
    return self._call_proxy(send)

  def get_courts(self):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts')
    return self._call_proxy(send)

  def get_filing_list(self, court_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts/{court_id}/filings')
    return self._call_proxy(send) 

  def get_filing(self, court_id:str, filing_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts/{court_id}/filings/{filing_id}')
    return self._call_proxy(send) 

  def get_policy(self, court_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts/{court_id}/policy')
    return self._call_proxy(send)

  def get_filing_status(self, court_id:str, filing_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts/{court_id}/filings/{filing_id}/status')
    return self._call_proxy(send)

  def cancel_filing_status(self, court_id:str, filing_id:str):
    send = lambda: self.proxy_client.delete(self.base_url + f'filingreview/courts/{court_id}/filings/{filing_id}')
    return self._call_proxy(send) 

  def check_filing(self, court_id:str, al_court_bundle:ALDocumentBundle):
    _recursive_give_data_url(al_court_bundle)
    all_vars = json.dumps(all_variables())
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts/{court_id}/filing/check', data=all_vars)
    return self._call_proxy(send)

  def file_for_review(self, court_id:str, al_court_bundle:ALDocumentBundle):
    _recursive_give_data_url(al_court_bundle)
    all_vars_obj = all_variables()
    all_vars = json.dumps(all_vars_obj)
    send = lambda: self.proxy_client.post(self.base_url + f'filingreview/courts/{court_id}/filings',
          data=all_vars)
    return self._call_proxy(send)

  def get_cases(self, court_id:str, person_name:IndividualName=None, docket_id:str=None) -> ApiResponse:
    #query_params = [('person_name', person_name), ('docket_id', docket_id)]
    #filtered_params = list(filter(lambda p: p[1] is not None, query_params))
    #print(filtered_params)
    #query_strs = urlencode(filtered_params)
    send = lambda: self.proxy_client.get(self.base_url + f'cases/courts/{court_id}/cases', 
        data=json.dumps({'person_name': person_name, 'docket_id': docket_id}))
    return self._call_proxy(send)

  def get_case(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/courts/{court_id}/cases/{case_id}')
    return self._call_proxy(send)

  def get_document(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/courts/{court_id}/cases/{case_id}/documents')
    return self._call_proxy(send)

  def get_service_attach_case_list(self, court_id:str, service_contact_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/courts/{court_id}/service-contacts/{service_contact_id}/cases')
    return self._call_proxy(send)

  def get_service_information(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/courts/{court_id}/cases/{case_id}/service-information')
    return self._call_proxy(send)

  def get_service_information_history(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/courts/{court_id}/cases/{case_id}/service-information-history')
    return self._call_proxy(send)
  
  def get_case_categories(self, court_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/categories')
    return self._call_proxy(send)
  
  def get_case_types(self, court_id:str, case_category:str, timing:str=None):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/case_types?category_id={case_category}&timing={timing}')
    return self._call_proxy(send)
  
  def get_case_subtypes(self, court_id:str, case_type:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/case_types/{case_type}/case_subtypes')
    return self._call_proxy(send)
  
  def get_filing_types(self, court_id:str, case_category:str, case_type:str, initial:bool):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/filing_types?category_id={case_category}&type_id={case_type}&initial={initial}')
    return self._call_proxy(send)
  
  def get_service_types(self, court_id:str): 
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/service_types')
    return self._call_proxy(send)
  
  def get_party_types(self, court_id:str, case_type_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/case_types/{case_type_id}/party_types')
    return self._call_proxy(send)
  
  def get_document_types(self, court_id:str, filing_type:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/filing_codes/{filing_type}/document_types')
    return self._call_proxy(send)
  
  def get_filing_components(self, court_id:str, filing_type:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/filing_codes/{filing_type}/filing_components')
    return self._call_proxy(send)
  
  def get_optional_services(self, court_id:str, filing_type:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/filing_codes/{filing_type}/optional_services')
    return self._call_proxy(send)
  
  def get_datafield(self, court_id:str, field_name:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/datafields/{field_name}')
    return self._call_proxy(send)
  
  def get_disclaimers(self, court_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'codes/courts/{court_id}/disclaimer_requirements')
    return self._call_proxy(send)
  
