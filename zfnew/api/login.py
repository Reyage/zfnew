# -*- coding: utf-8 -*-
"""
login.py - Authentication module for the Zhengfang (正方) educational system.

This module provides the Login class which handles:
  1. Fetching the login page and extracting the CSRF token.
  2. Retrieving the server's RSA public key (modulus + exponent).
  3. Encrypting the user's password with that RSA public key.
  4. POSTing the login form and persisting the session cookies.

Typical usage::

    from zfnew.api.login import Login

    lgn = Login(base_url='http://jwc.yourschool.edu.cn/')
    lgn.login('your_student_id', 'your_password')
    cookies = lgn.cookies          # requests.cookies.RequestsCookieJar
    cookies_str = lgn.cookies_str  # 'name1=val1; name2=val2; ...'
"""

import binascii
import rsa
import base64
import requests
from bs4 import BeautifulSoup
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, PKCS1_v1_5
from urllib import parse


class Login(object):
    """Handles authentication against the new-style Zhengfang educational system.

    Args:
        base_url (str): Root URL of the educational management system,
            e.g. ``'http://jwc.xhu.edu.cn/'``.

    Attributes:
        base_url (str): Root URL passed at construction time.
        key_url (str): Endpoint that returns the RSA public key as JSON
            (``/xtgl/login_getPublicKey.html``).
        login_url (str): The login form POST endpoint
            (``/xtgl/login_slogin.html``).
        headers (dict): Default HTTP request headers that mimic a real browser.
        sess (requests.Session): Persistent HTTP session that carries cookies
            between requests.
        cookies: Cookie jar populated after a successful :meth:`login` call.
        cookies_str (str): Semicolon-separated cookie string, useful for
            constructing raw ``Cookie`` headers.
    """

    def __init__(self, base_url):
        self.base_url = base_url
        # Derive endpoint URLs from the base URL so the class works for any school.
        self.key_url = parse.urljoin(base_url, '/xtgl/login_getPublicKey.html')
        self.login_url = parse.urljoin(base_url, '/xtgl/login_slogin.html')
        # Browser-like headers help avoid simple bot-detection on the server side.
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Referer': self.login_url
        }
        # A single Session object reuses the same TCP connection and automatically
        # stores cookies returned by the server, which is required for subsequent
        # authenticated requests.
        self.sess = requests.Session()
        self.cookies = ''
        self.cookies_str = ''

    def login(self, sid, password):
        """Log in to the educational system and store the resulting cookies.

        Steps performed:
          1. GET the login page to obtain the CSRF token embedded in the HTML.
          2. GET the public-key endpoint to retrieve the RSA modulus and exponent.
          3. Encrypt the plain-text password using :meth:`get_rsa`.
          4. POST the login form with the CSRF token, student ID, and
             encrypted password.
          5. Save the session cookies for use by subsequent API calls.

        Args:
            sid (str): Student ID (学号) used as the login username.
            password (str): Plain-text login password.
        """
        # Step 1: load the login page and parse the hidden CSRF token.
        req = self.sess.get(self.login_url, headers=self.headers)
        soup = BeautifulSoup(req.text, 'lxml')
        tokens = soup.find(id='csrftoken').get("value")

        # Step 2: fetch the RSA public key (returned as JSON with 'modulus' and 'exponent').
        res = self.sess.get(self.key_url, headers=self.headers).json()
        n = res['modulus']    # Base64-encoded RSA modulus
        e = res['exponent']   # Base64-encoded RSA public exponent

        # Step 3: encrypt the password with the server's RSA public key.
        hmm = self.get_rsa(password, n, e)

        # Step 4: submit the login form.
        # 'yhm' is the username field (学号), 'mm' is the encrypted password field (密码).
        # Note: Python dicts do not support duplicate keys; only the last value for 'mm'
        # is retained.  The duplicate assignment below is a no-op and can be removed
        # without any behavioural change.
        login_data = {
            'csrftoken': tokens,
            'yhm': sid,
            'mm': hmm
        }
        self.sess.post(self.login_url, headers=self.headers, data=login_data)

        # Step 5: persist cookies for later API calls.
        self.cookies = self.sess.cookies
        # Also expose a raw cookie string for callers that need it as a plain header.
        self.cookies_str = '; '.join([item.name + '=' + item.value for item in self.cookies])

    @classmethod
    def encrypt_sqf(cls, pkey, str_in):
        """Encrypt a string using a base64-encoded RSA public key via PKCS1 v1.5.

        .. note::
            Despite the parameter name ``pkey``, this method expects a
            *public* key, not a private key.  The naming is a legacy artifact.

        Args:
            pkey (str): Base64-encoded DER/PEM RSA public key.
            str_in (str): Plain-text string to encrypt.

        Returns:
            bytes: Base64-encoded ciphertext.
        """
        # Decode the base64 key bytes and import them as an RSA key object.
        private_key = pkey
        private_keybytes = base64.b64decode(private_key)
        prikey = RSA.importKey(private_keybytes)

        # Encrypt using PKCS1 v1.5 padding and return the result as base64.
        signer = PKCS1_v1_5.new(prikey)
        signature = base64.b64encode(signer.encrypt(str_in.encode("utf-8")))
        return signature

    @classmethod
    def get_rsa(cls, pwd, n, e):
        """Encrypt a password with an RSA public key supplied as base64-encoded components.

        The server returns the RSA key as two separate base64 strings (modulus
        and exponent).  This method reconstructs the :class:`rsa.PublicKey` from
        those components and uses it to encrypt the password.

        Args:
            pwd (str): Plain-text password to encrypt.
            n (str): Base64-encoded RSA modulus.
            e (str): Base64-encoded RSA public exponent.

        Returns:
            bytes: Base64-encoded RSA-encrypted password, ready to be POSTed
            as the ``mm`` form field.
        """
        message = str(pwd).encode()
        # Convert the base64-encoded modulus and exponent to hex strings,
        # then parse them as big integers to build the RSA public key.
        rsa_n = binascii.b2a_hex(binascii.a2b_base64(n))
        rsa_e = binascii.b2a_hex(binascii.a2b_base64(e))
        key = rsa.PublicKey(int(rsa_n, 16), int(rsa_e, 16))
        # Encrypt the password bytes and base64-encode the result for safe
        # transmission as a form field value.
        encropy_pwd = rsa.encrypt(message, key)
        result = binascii.b2a_base64(encropy_pwd)
        return result


