import streamlit as st
import requests
import nacl.secret
import nacl.hash
import zlib
import base64

def fetch(url):
  # Try to read as local file if url doesn't start with http
  if not url.lower().startswith('http'):
    with open(url, 'r') as f:
      return f.read()
  
  # Read as URL
  resp = requests.get(url)
  return resp.contents

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
  except Exception as e:
    raise ValueError('Incorrect password') from e
    
  return decrypted.decode('utf-8')