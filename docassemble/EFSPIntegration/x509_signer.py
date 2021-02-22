#!/usr/bin/env python3

from cryptography.hazmat.primitives.serialization import pkcs12 
from cryptography.hazmat.primitives.serialization import pkcs7 
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class HeaderSigner(object):
    """An object that handles signing contents using the private key of the
    Tyler issued x.509 certificate"""

    def __init__(self, certificate_file_path, password: str):
        cert_bytes = open(certificate_file_path, 'rb').read()
        full_cert_info = pkcs12.load_key_and_certificates(cert_bytes, password.encode())
        self._private_key = full_cert_info[0]
        self._certificate = full_cert_info[1]
    

    def sign_content(self, content):
        options = [pkcs7.PKCS7Options.DetachedSignature]
        # TODO(brycew): one of these signing params likely isn't correct: make sure it is
        return pkcs7.PKCS7SignatureBuilder().set_data(content.encode()
        ).add_signer(
            self._certificate, self._private_key, hashes.SHA256()
        ).sign(
            serialization.Encoding.PEM, options
        )