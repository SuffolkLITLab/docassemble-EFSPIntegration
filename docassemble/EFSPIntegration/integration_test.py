from docassemble.base.util import Address, Person, Individual
from ..efm_client import ProxyConnection, ApiResponse
import sys
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

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

class MockPerson:
  def __init__(self):
    self.email = 'fakeemail@example.com'
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
    self.address.zip = '12345'
    self.address.country = 'US'

  def sms_number(self) -> str:
    return '1234567890'

class TestClass:
  
  def __init__(self, proxy_conn, verbose:bool=True):
    self.proxy_conn = proxy_conn
    self.verbose = verbose

  def basic_assert(self, resp:ApiResponse):
    if self.verbose:
      print(resp)
    assert(resp.is_ok())
    return resp


  def test_self_user(self):
    myself = self.basic_assert(self.proxy_conn.get_user())
    assert(myself.data['middleName'] == 'Steven')
    nm = self.basic_assert(self.proxy_conn.update_user(myself.data['userID'], middle_name='Stephen'))
    bad_spelling = self.basic_assert(self.proxy_conn.get_user())
    assert(bad_spelling.data['middleName'] == 'Stephen')
    self.basic_assert(self.proxy_conn.update_user(myself.data['userID'], middle_name='Steven'))

    # Password stuff
    current_password = os.getenv('bryce_user_password')
    new_password = '12345678AbcDe!'
    email = os.getenv('bryce_user_email')
    changed_password = self.basic_assert(self.proxy_conn.self_change_password(current_password, new_password))
    self.basic_assert(self.proxy_conn.authenticate_user(tyler_email=email, tyler_password=new_password))
    changed_back = self.basic_assert(self.proxy_conn.self_change_password(new_password, current_password))
    self.basic_assert(self.proxy_conn.authenticate_user(tyler_email=email, tyler_password=current_password))

    self.basic_assert(self.proxy_conn.get_password_question(email)) 
    self.basic_assert(self.proxy_conn.get_notification_options())
    self.basic_assert(self.proxy_conn.get_notification_preferences())
    self.basic_assert(self.proxy_conn.update_notification_preferences(
      [{'code': 'SERVICEUNDELIVERABLE', 'isActive': False}]))
    new_notifs = self.basic_assert(self.proxy_conn.get_notification_preferences())
    assert(all(map(lambda n: n['isActive'] == False, 
        filter(lambda n: n['code'] == 'SERVICEUNDELIVERABLE', 
            new_notifs.data))))
    last_update = self.proxy_conn.update_notification_preferences([{'code': 'SERVICEUNDELIVERABLE', 'isActive': True}])
    assert(last_update.response_code == 200)


  def test_service_contacts(self):
    public =  self.basic_assert(self.proxy_conn.get_public_service_contacts(first_name='John'))
    new_contact = Individual()
    new_contact.name.first = 'Ella'
    new_contact.name.last = 'Doe'
    new_contact.email = 'ella.doe@example.com'
    new_contact.address.address = '123 Fakestreet Ave'
    new_contact.address.unit = 'Unit 999'
    new_contact.address.city = 'Boston'
    new_contact.address.state = 'MA'
    new_contact.address.zip = '12345'
    new_contact.address.country = 'US'
    new_contact.phone_number = '9727133770'
    new_c = self.basic_assert(self.proxy_conn.create_service_contact(new_contact, False, True, admin_copy='ella.doe@example.com'))
    contact_id = new_c.data
    self.basic_assert(self.proxy_conn.update_service_contact(contact_id, middleName='"Lorde"', email='different@example.com'))

    my_list = self.basic_assert(self.proxy_conn.get_service_contact_list())
    assert(len(my_list.data) >= 1)
    updated_contact = self.basic_assert(self.proxy_conn.get_service_contact(contact_id))
    assert(updated_contact.data['email'] == 'different@example.com')
    assert(updated_contact.data['middleName'] == '"Lorde"') 

    self.basic_assert(self.proxy_conn.attach_service_contact(contact_id, 'c6d795d1-3f89-411d-8c86-fa1a33fb88e5'))
    self.basic_assert(self.proxy_conn.detach_service_contact(contact_id, 'c6d795d1-3f89-411d-8c86-fa1a33fb88e5'))

    self.basic_assert(self.proxy_conn.remove_service_contact(contact_id))


  def test_firm(self): 
    firm = self.basic_assert(self.proxy_conn.get_firm())
    assert(firm.data['firmName'] == 'Suffolk LIT Lab')
    assert(firm.data['isIndividual'] == False)
    assert(firm.data['address']['addressLine1'] == '120 Tremont Street')

    update_firm = Person()
    update_firm.name.text = 'Suffolk FIT Lab'
    update_firm.address.address = '121 Tremont Street'
    resp = self.proxy_conn.update_firm(update_firm)
    assert(resp.response_code == 200)

    new_firm = self.basic_assert(self.proxy_conn.get_firm())
    assert(new_firm.data['firmName'] == 'Suffolk FIT Lab')
    assert(new_firm.data['address']['addressLine1'] == '121 Tremont Street')

    update_firm.name.text = 'Suffolk LIT Lab'
    update_firm.address.address = '120 Tremont Street'
    self.basic_assert(self.proxy_conn.update_firm(update_firm))


  def test_users(self):
    mock_person = MockPerson()
    firm_id = self.proxy_conn.get_firm().data['firmID']
    new_user = self.proxy_conn.register_user(mock_person, registration_type='FIRM_ADMIN_NEW_MEMBER', firm_name_or_id=firm_id)
    assert(new_user.response_code == 200)
    new_id = new_user.data['userID']

    self.basic_assert(self.proxy_conn.resend_activation_email(new_id))

    full_user = self.basic_assert(self.proxy_conn.get_user(new_id))
    assert(full_user.data['middleName'] == 'S')

    all_users = self.basic_assert(self.proxy_conn.get_users())
    assert(len(all_users.data) >= 2)

    roles = self.basic_assert(self.proxy_conn.get_user_roles(new_id))
    assert(len(roles.data) == 1)
    assert(roles.data[0]['roleName'] == 'FILER')

    new_role_add = self.proxy_conn.add_user_roles(new_id, [{'roleName': 'FIRM_ADMIN'}])
    assert(new_role_add.response_code == 204)

    new_roles = self.proxy_conn.get_user_roles(new_id)
    assert(any(map(lambda r: r['roleName'] == 'FIRM_ADMIN', new_roles.data)))
    rm_roles = self.proxy_conn.remove_user_roles(new_id, [{'roleName': 'FIRM_ADMIN'}])
    assert(rm_roles.response_code == 200)

    original_roles = self.proxy_conn.get_user_roles(new_id)
    assert(original_roles.response_code == 200)
    assert(roles.data == original_roles.data)

    self.basic_assert(self.proxy_conn.remove_user(new_id))


  def test_get_courts(self):
    courts = self.basic_assert(self.proxy_conn.get_courts())
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

    update_account = self.proxy_conn.update_global_payment_account(account_id,
        account_name='New, Better Name')
    if self.verbose:
      print(update_account)
    assert(update_account.response_code == 200)
    better_account = self.proxy_conn.get_global_payment_account(account_id) 
    assert(better_account.response_code == 200)
    assert(better_account.data['accountName'] == 'New, Better Name')

    update_account = self.proxy_conn.update_global_payment_account(account_id, 
        account_name=account.data['accountName'])
    assert(update_account.response_code == 200)


  def test_payment_accounts(self):
    self.basic_assert(self.proxy_conn.get_payment_account_type_list())
    self.basic_assert(self.proxy_conn.get_payment_account_list())

    new_account = self.basic_assert(self.proxy_conn.create_waiver_account('New Test account', False))
    id = new_account.data
    one_account = self.basic_assert(self.proxy_conn.get_payment_account(id))
    assert(one_account.data['accountName'] == 'New Test account')
    assert(one_account.data['paymentAccountID'] == id)

    self.basic_assert(self.proxy_conn.update_payment_account(id, account_name='New, Better Name'))
    better_account = self.basic_assert(self.proxy_conn.get_payment_account(id))
    assert(better_account.data['accountName'] == 'New, Better Name')

    self.basic_assert(self.proxy_conn.update_payment_account(id, account_name=one_account.data['accountName']))
    self.basic_assert(self.proxy_conn.remove_payment_account(new_account.data))

    global_account = self.basic_assert(self.proxy_conn.create_waiver_account('test global account', True))
    self.basic_assert(self.proxy_conn.remove_global_payment_account(global_account.data))


  def test_court_record(self):
    cases = self.basic_assert(self.proxy_conn.get_cases('adams', person_name={'first': 'John', 'last': 'Brown'}))
    assert(len(cases.data) > 0)
    case_id = cases.data[0]['value']['caseTrackingID']['value']
    case = self.basic_assert(self.proxy_conn.get_case('adams', case_id))
    doc_resp = self.proxy_conn.get_document('adams', case_id)
    assert(doc_resp.response_code == 405)
    serv_info = self.basic_assert(self.proxy_conn.get_service_information('adams', case_id))
    history_serv_info = self.basic_assert(self.proxy_conn.get_service_information_history('adams', case_id))

    serv_id = 'abcd'  # serv_info.data[0]
    attach_cases = self.proxy_conn.get_service_attach_case_list('adams', serv_id)
    if self.verbose:
      print(attach_cases)


  def test_attorneys(self):
    new_attorney = self.proxy_conn.create_attorney(bar_number='6224951', first_name='Valarie', 
        middle_name='DONTUSE_IS_REAL_PERSON', last_name='Franklin')
    assert(new_attorney.response_code == 200)
    new_attorney_id = new_attorney.data

    attorney_list = self.basic_assert(self.proxy_conn.get_attorney_list())
    assert(any(map(lambda a: a['barNumber'] == '6224951', attorney_list.data)))

    updated_attorney = self.basic_assert(self.proxy_conn.update_attorney(
        new_attorney_id, middle_name='Lobert'))
    assert(updated_attorney.data is not None)

    full_new_attorney = self.basic_assert(self.proxy_conn.get_attorney(new_attorney_id))
    assert(full_new_attorney.data['middleName'] == 'Lobert')

    deleted_maybe = self.proxy_conn.remove_attorney(new_attorney_id)
    assert(deleted_maybe.response_code == 200)

  def test_filings(self):
    filing_list = self.basic_assert(self.proxy_conn.get_filing_list('adams', start_date=datetime.today() - timedelta(days=3), end_date=datetime.today()))
    policy = self.basic_assert(self.proxy_conn.get_policy('adams'))

    cdir = Path(__file__).resolve().parent
    all_vars_str = cdir.joinpath('initial_cook_filing_vars_shorter.json').open('r').read()
    base_url = self.proxy_conn.base_url
    court = 'cook:cvd1'
    fees_send = lambda: self.proxy_conn.proxy_client.post(base_url + f'filingreview/courts/{court}/filing/fees', data=all_vars_str)
    fees_resp = self.basic_assert(self.proxy_conn._call_proxy(fees_send))
    check_send = lambda: self.proxy_conn.proxy_client.get(base_url + f'filingreview/courts/{court}/filing/check', data=all_vars_str)
    checked_resp = self.basic_assert(self.proxy_conn._call_proxy(check_send))
    file_send = lambda: self.proxy_conn.proxy_client.post(base_url + f'filingreview/courts/{court}/filings', data=all_vars_str)
    filing_resp = self.basic_assert(self.proxy_conn._call_proxy(file_send)) 

    for filing_id in filing_resp.data:
      status_resp = self.basic_assert(self.proxy_conn.get_filing_status(court, filing_id))
      detail_resp = self.basic_assert(self.proxy_conn.get_filing(court, filing_id))
      cancel_resp = self.basic_assert(self.proxy_conn.cancel_filing_status(court, filing_id))

def main(args):
  base_url = get_proxy_server_ip()
  api_key = os.getenv('PROXY_API_KEY')
  proxy_conn = ProxyConnection(url=base_url, api_key=api_key)
  resp = proxy_conn.authenticate_user(tyler_email=os.getenv('bryce_user_email'), 
      tyler_password=os.getenv('bryce_user_password'))
  assert(resp.response_code == 200)
  tc = TestClass(proxy_conn, verbose=True)
  tc.test_self_user()
  tc.test_firm()
  tc.test_service_contacts()
  tc.test_get_courts()
  tc.test_global_payment_accounts()
  tc.test_payment_accounts()
  tc.test_attorneys()
  tc.test_court_record()
  tc.test_users()
  tc.test_filings()

if __name__ == '__main__':
  main(sys.argv)
