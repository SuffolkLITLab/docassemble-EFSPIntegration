#!/usr/bin/env python3

import json
import logging
from typing import List
import http.client as http_client

from urllib.parse import urlencode
import requests
from docassemble.base.functions import all_variables, get_config
from docassemble.base.util import IndividualName
from docassemble.AssemblyLine.al_document import ALDocumentBundle

class ApiResponse:
  def __init__(self, response_code, error_msg:str, data):
    self.response_code = response_code
    self.error_msg = error_msg
    self.data = data

  def __str__(self):
    if self.error_msg:
      return f'response_code: {self.response_code}, error_msg: {self.error_msg}, data: {self.data}'
    return f'response_code: {self.response_code}, data: {self.data}'

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
    self.verbose = False
    self.authed_user_id = None
    self.set_verbose_logging(True)

  def _call_proxy(self, send_func):
    try:
      resp = send_func()
      if resp.status_code == 401:
        auth_resp = self.AuthenticateUser()
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
      resp = self.proxy_client.post(self.base_url + 'adminusers/authenticate/', 
        data=json.dumps(auth_obj))
      if resp.status_code == requests.codes.ok:
        self.active_token = resp.json()
        self.proxy_client.headers['X-API-KEY'] = self.active_token
        # self.authed_user_id = data['userID']
    except requests.ConnectionError as ex:
      return ProxyConnection.user_visible_resp(
        f'Could not connect to the Proxy server at {self.base_url}')
    return ProxyConnection.user_visible_resp(resp)

  def register_user(self, person_to_reg, password:str, registration_type:str='INDIVIDUAL'):
    reg_obj = {
          'registrationType': registration_type,
          'email': person_to_reg.email,
          'firstName': person_to_reg.name.first,
          'middleName': person_to_reg.name.middle,
          'lastName': person_to_reg.name.last,
          'password': password,
          'streetAddressLine1': person_to_reg.address.address,
          'streetAddressLine2': person_to_reg.address.unit,
          'city': person_to_reg.address.city,
          'stateCode': person_to_reg.address.state,
          'zipCode': person_to_reg.address.zip_code,
          'countryCode': person_to_reg.address.country,
          # only grabs the first 10 digits of the phone number
          'phoneNumber': person_to_reg.sms_number()[-10:]
    }

    send = lambda: self.proxy_client.put(self.base_url + 'adminusers/users', data=json.dumps(reg_obj))
    return self._call_proxy(send)

  # Managing Firm Users

  def get_user_list(self):
    send = lambda: self.proxy_client.get(self.base_url + 'adminusers/users')
    return self._call_proxy(send)

  def get_user(self, id:str):
    #if id is None:
    #    id = self.authed_user_id
    send = lambda: self.proxy_client.get(self.base_url + f'adminusers/users/{id}')
    return self._call_proxy(send)

  def get_user_role(self, id:str):
    #if id is None:
    #    id = self.authed_user_id
    resp = self.proxy_client.get(self.base_url + f'adminuser/users/{id}/roles')
    return ProxyConnection.user_visible_resp(resp)

  def add_user_role(self, roles:List[dict], id:str):
    #if id is None:
    #    id = self.authed_user_id
    resp = self.proxy_client.post(self.base_url + f'adminusers/users/{id}/roles', 
      data=json.dumps(roles))
    return ProxyConnection.user_visible_resp(resp)

  def remove_user_role(self, roles:List[dict], id:str):
      #if id is None:
      #    id = self.authed_user_id
      resp = self.proxy_client.delete(self.base_url + f'adminuser/users/{id}/roles')
      return ProxyConnection.user_visible_resp(resp)

  def ChangePassword(self):
    # TODO
    resp = self.proxy_client.post(self.base_url + f'adminuser/users/{id}/password')
    return ProxyConnection.user_visible_resp(None)

  def self_resend_activation_email(self, email: str):
    send = lambda: self.proxy_client.post(self.base_url + 'adminusers/user/resend_activation_email',
        data=email)
    return self._call_proxy(send) 

  # TODO(brycew): not tested
  def resend_activation_email(self, id:str):
      #if id is None:
      #    id = self.authed_user_id
      resp = self.proxy_client.post(self.base_url + f'adminusers/users/{id}/resend_activation_email')
      return ProxyConnection.user_visible_resp(resp)

  # TODO(brycew): not tested
  def update_notification_preferences(self, **kwargs):
    # TODO
    resp = self.proxy_client.put(self.base_url + f'adminuser/users/{id}/update_notification_preferences', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  # TODO(brycew): not tested
  def get_notification_preference_options(self):
    send = lambda: self.proxy_client.get(self.base_url + 'adminusers/notification_options').json()
    return self._call_proxy(send)

  # TODO(brycew): not tested
  def update_user(self, email:str, first_name:str, middle_name:str, last_name:str, id:str):
    updated_user = {'email': email, 'firstName': first_name, 'middleName': middle_name, 'lastName': last_name}
    #if id is None:
    #    id = self.authed_user_id
    # TODO: qs: should this method be PUT, not POST?
    resp = self.proxy_client.post(self.base_url + f'adminusers/users/{id}', data=json.dumps(updated_user))
    return ProxyConnection.user_visible_resp(resp)

  def remove_user(self, id:str):
      #if id is None:
      #    id = self.authed_user_id
      resp = self.proxy_client.delete(self.base_url + f'adminusers/users/{id}')
      return ProxyConnection.user_visible_resp(resp)

  # TODO(brycew): not tested
  def reset_user_password(self, email:str):
    resp = self.proxy_client.post(self.base_url + 'adminusers/user/reset_password', data=email)
    return ProxyConnection.user_visible_resp(resp)

  # Managing a Firm
  def get_firm(self):
    send = lambda: self.proxy_client.get(self.base_url + 'firmattorneyservice/firm')
    return self._call_proxy(send)

  def update_firm(self, firm_id, **kwargs):
    # TODO
    resp = self.proxy_client.put(self.base_url + f'firmattorneyservice/firms/{firm_id}/update', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  # Managing Attorneys
  def get_attorney_list(self, firm_id):
    # TODO
    resp = self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/attorneys')
    return ProxyConnection.user_visible_resp(None)

  def get_attorney(self, firm_id, attorney_id):
    # TODO
    resp = self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/attorneys/{attorney_id}')
    return ProxyConnection.user_visible_resp(None)

  def update_attorney(self, firm_id, attorney_id, **kwargs):
    # TODO
    resp = self.proxy_client.put(self.base_url + f'firmattorneyservice/firms/{firm_id}/attorneys/{attorney_id}', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  def create_attorney(self, firm_id, **kwargs):
    # TODO
    resp = self.proxy_client.post(self.base_url + f'firmattorneyservice/firms/{firm_id}/attorneys', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  def remove_attorney(self, firm_id, attorney_id):
    # TODO
    resp = self.proxy_client.delete(self.base_url + f'firmattorneyservice/firms/{firm_id}/attorneys/{attorney_id}')
    return ProxyConnection.user_visible_resp(None)

  # Managing Payment Accounts
  def get_payment_account_type_list(self, firm_id):
    # TODO
    resp = self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/payment_accounts/types')
    return ProxyConnection.user_visible_resp(None)

  def get_payment_account_list(self, firm_id):
    # TODO
    resp = self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/payment_accounts')
    return ProxyConnection.user_visible_resp(None)

  def get_payment_account(self, firm_id, payment_account_id):
    # TODO
    resp = self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/payment_accounts/{payment_account_id}')
    return ProxyConnection.user_visible_resp(None)

  def update_payment_account(self, firm_id, payment_account_id, **kwargs):
    # TODO
    resp = self.proxy_client.put(self.base_url + f'firmattorneyservice/firms/{firm_id}/payment_accounts', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  def create_payment_account(self, firm_id, **kwargs):
    # TODO
    resp = self.proxy_client.post(self.base_url + f'firmattorneyservice/firms/{firm_id}/payment_accounts', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  def remove_payment_account(self, firm_id, payment_account_id):
    # TODO
    resp = self.proxy_client.delete(self.base_url + f'firmattorneyservice/firms/{firm_id}/payment_accounts/{payment_account_id}')
    return ProxyConnection.user_visible_resp(None)

  # Managing Service Contacts
  # Service contacts are part of the `firm` hierarchy
  def get_service_contact_list(self, firm_id):
    # TODO
    resp = self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts')
    return ProxyConnection.user_visible_resp(None)

  def get_service_contact(self, firm_id, service_contact_id):
    # TODO
    resp = self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts/{service_contact_id}')
    return ProxyConnection.user_visible_resp(None)

  def update_service_contact(self, firm_id, service_contact_id, **kwargs):
    # TODO
    resp = self.proxy_client.put(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts/{service_contact_id}', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  def create_service_contact(self, firm_id, **kwargs):
    # TODO
    resp = self.proxy_client.post(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts')
    return ProxyConnection.user_visible_resp(None)

  def remove_service_contact(self, firm_id, service_contact_id):
    # TODO
    resp = self.proxy_client.delete(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts/{service_contact_id}')
    return ProxyConnection.user_visible_resp(None)

  # Using Service Contacts
  def attach_service_contact(self, firm_id, service_contact_id, **kwargs):
    # TODO
    resp = self.proxy_client.put(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts/attach/{service_contact_id}')
    return ProxyConnection.user_visible_resp(None)

  def detach_service_contact(self, firm_id, service_contact_id, **kwargs):
    # TODO
    send = lambda: self.proxy_client.put(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts/detach/{service_contact_id}')
    return ProxyConnection.user_visible_resp(None)

  # TODO(QS): should this name include ServiceContact?
  def get_public_list(self, firm_id):
    # TODO
    send = lambda: self.proxy_client.get(self.base_url + f'firmattorneyservice/firms/{firm_id}/service_contacts/public_list')
    return ProxyConnection.user_visible_resp(None)

  # Global Payment Accounts
  def get_global_payment_account_list(self):
    # TODO
    send = lambda: self.proxy_client.get(self.base_url + f'payments/global-accounts')
    return ProxyConnection.user_visible_resp(None)

  def get_global_payment_account(self, global_payment_account_id):
    # TODO
    send = lambda: self.proxy_client.get(self.base_url + f'payments/global-accounts/{global_payment_account_id}')
    return self._call_proxy(send) 

  def update_global_payment_account(self, global_payment_account_id, **kwargs):
    # TODO
    send = lambda: self.proxy_client.put(self.base_url + f'payments/global-accounts/{global_payment_account_id}', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  def create_global_payment_account(self, **kwargs):
    # TODO
    send = lambda: self.proxy_client.post(self.base_url + f'payments/global-accounts', data=json.dumps(kwargs))
    return ProxyConnection.user_visible_resp(None)

  def remove_global_payment_account(self, global_payment_account_id):
    # TODO
    send = lambda: self.proxy_client.delete(self.base_url + f'payments/global-accounts/{global_payment_account_id}')
    return ProxyConnection.user_visible_resp(None)

  # TODO(QS): should this name include ServiceContact?
  def get_public_list(self, firm_id):
    return ProxyConnection.user_visible_resp(None)

  def get_courts(self):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts')
    return self._call_proxy(send)

  def get_filing_list(self, court_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts/{court_id}/filings')
    return self._call_proxy(send) 

  def get_filing(self, court_id:str, filing_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts/{court_id}/filings/{filing_id}')
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
    send = lambda: self.proxy_client.post(self.base_url + f'filingreview/courts/{court_id}/check_filing', data=all_vars)
    return self._call_proxy(send)

  def file_for_review(self, court_id:str, al_court_bundle:ALDocumentBundle):
    _recursive_give_data_url(al_court_bundle)
    all_vars_obj = all_variables()
    all_vars_obj['tyler_payment_id'] = get_config('efile proxy').get('tyler payment id')
    all_vars = json.dumps(all_vars_obj)
    send = lambda: self.proxy_client.post(self.base_url + f'filingreview/courts/{court_id}/filings',
          data=all_vars)
    return self._call_proxy(send)

  def get_cases(self, court_id:str, person_name:IndividualName=None, docket_id:str=None) -> ApiResponse:
    #query_params = [('person_name', person_name), ('docket_id', docket_id)]
    #filtered_params = list(filter(lambda p: p[1] is not None, query_params))
    #print(filtered_params)
    #query_strs = urlencode(filtered_params)
    send = lambda: self.proxy_client.get(self.base_url + f'cases/court/{court_id}/case', 
        data=json.dumps({'person_name': person_name}))
    return self._call_proxy(send)

  def get_case(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/court/{court_id}/case/{case_id}')
    return self._call_proxy(send)

  def get_document(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/court/{court_id}/case/{case_id}/document')
    return self._call_proxy(send)

  def get_service_attach_case_list(self, court_id:str, service_contact_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/court/{court_id}/service_contact/{service_contact_id}/cases')
    return self._call_proxy(send)

  def get_service_information(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/court/{court_id}/case/{case_id}/service_information')
    return self._call_proxy(send)

  def get_service_information_history(self, court_id:str, case_id:str):
    send = lambda: self.proxy_client.get(self.base_url + f'cases/court/{court_id}/case/{case_id}/service_information_history')
    return self._call_proxy(send)

"""
class MockPerson:
  def __init__(self):
    self.email = 'thesurferdude@comcast.net'
    # Neat trick: https://stackoverflow.com/a/24448351/11416267
    self.name = type('', (), {})()
    self.name.first = 'B'
    self.name.middle = 'S'
    self.name.last = 'W'
    self.address = type('', (), {})()
    self.address.address = '123 Fakestreet Ave'
    self.address.unit = 'Apt 1'
    self.address.city = 'Boston'
    self.address.state = 'MA'
    self.address.zip_code = '12345'
    self.address.country = 'US'

  def sms_number(self) -> str:
    return '1234567890'
"""
