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


def test_get_firm(proxy_conn):
  firm = proxy_conn.GetFirm()
  print(firm)
  assert(firm.response_code == 200)
  assert(firm.data['firmName'] == 'Suffolk LIT Lab')
  assert(firm.data['isIndividual'] == False)
  assert(firm.data['address']['addressLine1'] == '120 Tremont Street')

def test_get_courts(proxy_conn):
  courts = proxy_conn.GetCourts()
  print(courts)
  assert(courts.response_code == 200)
  assert('Jefferson' in courts.data)


def main(args):
  # Just writitng the test however now. Get something down.
  base_url = get_proxy_server_ip()
  api_token = os.getenv('PROXY_API_KEY')
  proxy_conn = ProxyConnection(url=base_url, api_token=api_token)
  resp = proxy_conn.AuthenticateUser(email=os.getenv('bryce_user_email'), 
      password=os.getenv('bryce_user_password'))
  assert(resp.response_code == 200)
  test_get_firm(proxy_conn)
  test_get_courts(proxy_conn)

if __name__ == '__main__':
  main(sys.argv)

