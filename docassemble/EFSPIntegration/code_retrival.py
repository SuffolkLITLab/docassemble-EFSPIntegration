#!/usr/bin/env python3

import os
import requests
import base64
from .x509_signer import HeaderSigner
import http.client as http_client
import logging
import datetime

class CodeRetrival(object):
    def __init__(self, base_url: str, signer: HeaderSigner):
        """base_url should not contain the trailing slash"""
        self.base_url = base_url
        self.signer = signer

    
    @staticmethod
    def verbose_logging(turn_on: bool):
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True


    def get_location_codes(self):
        full_url = self.base_url + '/CodeService/codes/location'
        auth_header = base64.b64encode(self.signer.sign_content(datetime.datetime.now().isoformat()))
        resp = requests.get(full_url, headers={'tyl-efm-api': auth_header})
        print(resp.request)
        return resp

if __name__ == '__main__':
    signer = HeaderSigner('../x509_stuff/Suffolk.pfx', os.environ['x509_password'])
    code_ret = CodeRetrival(os.environ['base_url'], signer)
    code_ret.verbose_logging(True)
    resp = code_ret.get_location_codes()
    with open('test.zip', 'wb') as f:
        f.write(resp.content)
    
