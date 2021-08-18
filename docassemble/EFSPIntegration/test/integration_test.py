from ..efm_client import ProxyConnection
import sys
import subprocess
import json
import os

def get_proxy_server_ip():
  # Figure out the ip addr of the service, assuming it's running through
  # Docker compose
  info_json = subprocess.check_output(['docker', 'inspect', 'efileproxyserver_efspjava_1'])
  if info_json:
    info_dict = json.loads(info_json)
    base_url = 'http://' \
        + info_dict[0]['NetworkSettings']['Networks']['efileproxyserver_default']['IPAddress'] \
        + ':9000/'
    print('Using URL: ' + base_url)
    return base_url
  else:
    print("FAILED Can't find the docker image!")
    return None


class TestClass:
  
  def __init__(self, proxy_conn, verbose:bool=True):
    self.proxy_conn = proxy_conn
    self.verbose = verbose

  def test_get_firm(self): 
    firm = self.proxy_conn.get_firm()
    if self.verbose:
      print(firm)
    assert(firm.response_code == 200)
    assert(firm.data['firmName'] == 'Suffolk LIT Lab')
    assert(firm.data['isIndividual'] == False)
    assert(firm.data['address']['addressLine1'] == '120 Tremont Street')

  def test_get_courts(self):
    courts = self.proxy_conn.get_courts()
    if self.verbose:
      print(courts)
    assert(courts.response_code == 200)
    assert('jefferson' in courts.data)

  def test_global_payment_accounts(self):
    all_accounts = self.proxy_conn.get_global_payment_account_list()
    if self.verbose:
      print(all_accounts)
    assert(all_accounts.response_code == 200)
    assert(all_accounts.data[0]['firmID'] is None)
    account_id = all_accounts.data[0]['paymentAccountID']
    account = self.proxy_conn.get_global_payment_account(global_payment_account_id=account_id)
    if self.verbose:
      print(account)
    assert(account.response_code == 200)
    assert(account.data['paymentAccountID'] == account_id)

  def test_payment_accounts(self):
    payment_types = self.proxy_conn.get_payment_account_types()
    assert(payment_types.response_code == 200)
    if self.verbose:
      print(payment_types.data)
    all_accounts = self.proxy_conn.get_payment_account_list()
    assert(all_accounts.response_code == 200)
    if self.verbose:
      print(all_accounts)

  def test_court_record(self):
    cases = self.proxy_conn.get_cases('adams', person_name={'first': 'John', 'last': 'Brown'})
    assert(cases.response_code == 200)
    assert(len(cases.data) > 0)
    if self.verbose:
      print(cases)
    case_id = cases.data[0]['value']['caseTrackingID']['value']
    case = self.proxy_conn.get_case('adams', case_id)
    assert(case.response_code == 200)
    if self.verbose:
      print(case)
    doc_resp = self.proxy_conn.get_document('adams', case_id)
    assert(doc_resp.response_code == 405)
    serv_info = self.proxy_conn.get_service_information('adams', case_id)
    assert(serv_info.response_code == 200)
    if self.verbose:
      print(serv_info)
    history_serv_info = self.proxy_conn.get_service_information_history('adams', case_id)
    assert(history_serv_info.response_code == 200)
    if self.verbose:
      print(history_serv_info)

    serv_id = 'abcd'  # serv_info.data[0]
    attach_cases = self.proxy_conn.get_service_attach_case_list('adams', serv_id)
    if self.verbose:
      print(attach_cases)

def main(args):
  # Just writitng the test however now. Get something down.
  base_url = get_proxy_server_ip()
  api_key = os.getenv('PROXY_API_KEY')
  proxy_conn = ProxyConnection(url=base_url, api_key=api_key)
  resp = proxy_conn.authenticate_user(tyler_email=os.getenv('bryce_user_email'), 
      tyler_password=os.getenv('bryce_user_password'))
  assert(resp.response_code == 200)
  tc = TestClass(proxy_conn, verbose=True)
  tc.test_get_firm()
  tc.test_get_courts()
  tc.test_global_payment_accounts()
  tc.test_court_record()

if __name__ == '__main__':
  main(sys.argv)

