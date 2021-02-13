import click
import nacl.secret
import nacl.utils
import nacl.hash
import sys
import zlib
import base64

from . import __version__

def kdf(size, pwd):
  """ Generate appropriate sized key from password """
  return nacl.hash.blake2b(pwd, digest_size=size)[:size]

def encrypt(fname, pwd):
  # Read & gzip file
  with open(fname, 'rb') as f:
    contents = f.read()
    zipd = zlib.compress(contents)
  
  # Hash password to appropriate size key
  pwdbytes = pwd.encode('utf-8')
  key = kdf(nacl.secret.SecretBox.KEY_SIZE, pwdbytes)

  # Encrypt
  box = nacl.secret.SecretBox(key)
  enc = box.encrypt(zipd)
  
  # Base 64 encode
  enc64 = base64.b64encode(enc).decode("ascii")
  
  # Store the data
  outfname = fname+'.enc'
  with open(outfname, 'w') as f:
    f.write(enc64)
    
  return outfname

def decrypt(fname, pwd):
  # Read file
  with open(fname, 'r') as f:
    enc64 = f.read()
  
  # Base 64 decode
  zipd = base64.b64decode(enc64)
  
  # Hash password to appropriate size key
  pwdbytes = pwd.encode('utf-8')
  key = kdf(nacl.secret.SecretBox.KEY_SIZE, pwdbytes)

  # Decrypt
  box = nacl.secret.SecretBox(key)
  zipd = box.decrypt(zipd)
  
  # Ungzip
  contents = zlib.decompress(zipd)
  
  return contents

# ---------------------------------------------------------------------------

@click.command()
@click.version_option(version=__version__)
@click.option('-e', '--encrypt', 'srcfile', help='Encrypt a data file')
@click.option('-d', '--decrypt', 'encfile', help='Decrypt a data file')
def main(srcfile, encfile):
  """Command line tools for cleaning data prior to using for dashboard"""
  
  # --encrypt INPUT_FILE; prompt for password and write encrypted text to INPUT_FILE.enc
  if srcfile:
    pwd = click.prompt('Password', hide_input=True)
    outfname = encrypt(srcfile, pwd)
    click.echo(srcfile + ' encrypted to ' + outfname)

  # --decrypt ENCRYPTED_FILE; prompt for password and print decrypted text
  if encfile:
    pwd = click.prompt('Password', hide_input=True)
    dec = decrypt(encfile, pwd)
    click.echo(dec)
