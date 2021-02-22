#!/usr/bin/env python3

import os
import requests
import base64
from .x509_signer import HeaderSigner
import http.client as http_client
import logging
import datetime

class CodeRetrival(object):
    def __init__(self, base_url, signer):
        """base_url should not contain the trailing slash"""
        self.base_url = base_url
        self.signer = signer

    
    @staticmethod
    def verbose_logging(turn_on):
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

