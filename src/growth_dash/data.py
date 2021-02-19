import streamlit as st
import requests
import nacl.secret
import nacl.hash
import zlib
import base64
import logging
from pprint import pformat

def fetch(url):
  logging.info('Fetching ' + url)

  # Try to read as local file if url doesn't start with http
  if not url.lower().startswith('http'):
    with open(url, 'r') as f:
      return f.read()
  
  # Read as URL
  with requests.get(url, allow_redirects=True) as resp:
    logging.info('Status ' + str(resp.status_code) + ' from ' + resp.url + '\n Headers: ' + pformat(resp.headers))

    resp.raise_for_status()
    return resp.content

def kdf(size, pwd):
  """ Generate appropriate sized key from password """
  return nacl.hash.blake2b(pwd, digest_size=size)[:size]

def decrypt(contents, pwd):
  """ Decrypt encrypted string, which should be gzipped, encrypted with pynacl, and base64 encoded. """
  
  # Base 64 decode
  decoded = base64.b64decode(contents)
  
  # Try to decrypt if a password was provided
  if pwd is not None:
    # Hash password to appropriate size key
    pwdbytes = pwd.encode('utf-8')
    key = kdf(nacl.secret.SecretBox.KEY_SIZE, pwdbytes)
  
    # Decrypt
    box = nacl.secret.SecretBox(key)
    zipd = box.decrypt(decoded)

  else:
    zipd = decoded
    
  
  # Ungzip
  unzipped = zlib.decompress(zipd)
  
  return unzipped

@st.cache
def load_data(src, pwd=None):
  
  if src is None:
    return None
  
  # Fetch source data URL
  contents = fetch(src)

  # Decrypt
  try:
    decrypted = decrypt(contents, pwd)
  except (nacl.exceptions.CryptoError, zlib.error) as e:
    logging.warn(str(e) + ' while decrypting source data. Assuming incorrect password.', exc_info=True)
    raise ValueError('Incorrect password') from e
    
  return decrypted.decode('utf-8')