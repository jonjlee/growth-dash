import streamlit as st
import pandas as pd
import numpy as np
import io
import requests
import nacl.secret
import nacl.hash
import zlib
import base64
import logging

from dataclasses import dataclass

DAYS_PER_MONTH=30.4375

@dataclass
class GrowthData:
  """
  Patient data.
  - df: the full data set imported from the source file
  - wt: all weight measurements
  - ht: all height measurements
  - hc: all head circumference measurements
  - mrns: list of all unique MRNs in the data set
  """
  df: pd.DataFrame
  wt: pd.DataFrame
  mrns: list

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

def parse(byts):
  """
  Use pandas.read_csv() to create a data frame from CSV data since the rest of our
  program uses pandas to manipulate data
  """
  return pd.read_csv(
    # Wrap byte array in stream (stackoverflow.com/questions/22604564/create-pandas-dataframe-from-a-string)
    io.BytesIO(byts),
    
    # explicitly specify first row is a header row, then overwrite contents
    # with our own column names in names[]
    header=0,
    names=['MRN', 'Name', 'DOB', 'Metric', 'Val', 'TS', 'Row', 'Misc'],
    
    # Columns with datetime data to parse
    parse_dates=['DOB', 'TS'],
    infer_datetime_format=True,
    
    # return only the columns we want
    usecols=['MRN', 'DOB', 'Metric', 'Val', 'TS']
  )

# Use allow_output_mutation to avoid hashing return value to improve performance
@st.cache(allow_output_mutation=True)
def load_data(src, pwd=None):
  """
  Fetch source data from file or URL, src, and decrypt with given password.
  Parse data as CSV and do basic preprocessing.
  """
  
  if src is None:
    return None
  
  # Fetch source data URL
  contents = fetch(src)

  # Decrypt
  try:
    decrypted_bytes = decrypt(contents, pwd)
  except (nacl.exceptions.CryptoError, zlib.error) as e:
    logging.warn(str(e) + ' while decrypting source data. Assuming incorrect password.', exc_info=True)
    raise ValueError('Incorrect password') from e
  
  # Parse text data into pandas data frame
  df = parse(decrypted_bytes)

  return df

# Use allow_output_mutation to avoid hashing return value to improve performance
@st.cache(allow_output_mutation=True, show_spinner=False)
def transform(df):
  """
  Preprocess data non-destructively. For example, adds column for Age in months.

  Returns:
    
    {
      'df': entire filtered data set,
      'wt': weight measurements,
      'ht': height measurements,
      'hc': head circumference measurements,
      'mrns': unique MRNs
    }
  """
  
  # Copy original data frame, sorted by MRN
  df = df.sort_values(by='MRN', ignore_index=True)

  # Precalculate age in months for each measurement
  df['Age'] = (
    (df['TS'] - df['DOB']).dt.days / DAYS_PER_MONTH
  ).round(2)
  
  # Remove rows for measurements taken after 2 yo
  df = df.loc[df['Age'] < 24.5]

  # Build a dataframe with info for each unique patient MRN
  ptinfo = df.groupby(['MRN']).agg({
    'TS': 'min', # time stamp of the first visit
    'Sex': 'first',
    'DOB': 'first'
  })
  
  # Calculate each patient's age in months
  now = np.datetime64('today')
  one_month = np.timedelta64(1, 'M')
  ptinfo['AgeInMos'] = (now - ptinfo['DOB']) / one_month
  
  
  # Filter specific measurements types
  wtdata = df.loc[df['Metric'] == 'Weight Measured']
  htdata = df.loc[df['Metric'] == 'Height/Length Measured']
  
  # Get list of unique MRNs
  mrns = ptinfo.index.unique().tolist()
  
  return GrowthData(
    df=df,
    wt=wtdata,
    mrns=mrns
  )