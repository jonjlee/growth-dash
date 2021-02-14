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

def decrypt(encrypted, pwd):
  """ Decrypt encrypted string, which should be gzipped, encrypted with pynacl, and base64 encoded. """
  
  # Base 64 decode
  zipd = base64.b64decode(encrypted)
  
  # Hash password to appropriate size key
  pwdbytes = pwd.encode('utf-8')
  key = kdf(nacl.secret.SecretBox.KEY_SIZE, pwdbytes)

  # Decrypt
  box = nacl.secret.SecretBox(key)
  zipd = box.decrypt(zipd)
  
  # Ungzip
  contents = zlib.decompress(zipd)
  
  return contents

@st.cache
def load_data(src, pwd):
  
  # Fetch source data URL
  
  
  # Decrypt
  with open(src, 'r') as f:
    encrypted = f.read()
    contents = decrypt(encrypted, pwd)

  return contents.decode('utf-8')