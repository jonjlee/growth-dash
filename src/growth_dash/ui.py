import streamlit as st
import html
import base64
import pandas as pd
from . import gc_stats as gc
from .data import load_data

# Main raw source data file
DATA = None

def ensure_data_loaded():
  """
  Get source data file location from URL and try to load/decrypt it.
  Returns parsed source data as an object, or None if there was an error.
  If data could not be loaded, an appropriate error message and prompt will be added to UI.
  """
  
  # Source data location passed in as query param (https://.../?src=)
  qps = st.experimental_get_query_params()
  src_qp = qps.get('src', [None])[0]
  pwd_qp = qps.get('pwd', [None])[0]
  
  # Password in URL is base 64 encoded
  if pwd_qp:
    try:
      pwd_qp = base64.b64decode(pwd_qp).decode('ascii')
    except:
      pwd_qp = None
  
  # Error if no source data file specified
  if src_qp is None:
    st.write('<font color="red">No source file specified. Please reload this page using the link that was provided.</font>', unsafe_allow_html=True)
    return None
    
  # Placeholder for error message and password prompt if needed
  st_error = st.empty()
  with st_error.beta_container():
    pwd_err_field = st.empty()
    pwd_field = st.text_input('Enter password:', pwd_qp or '', type='password')
    pwd_submit = st.button('Submit')
  
  # Prefer user input to query param
  pwd = pwd_field or pwd_qp

  # Update URL to include current password
  if pwd:
    qps['pwd'] = base64.b64encode(pwd.encode('ascii')).decode('ascii')
    st.experimental_set_query_params(**qps)
  
  # Fetch/decrypt data
  data = None
  try:
    data = load_data(src_qp, pwd)
  except FileNotFoundError:
    st_error.write('<font color="red">Could not locate the data file ' + src_qp + '</font>', unsafe_allow_html=True)
  except ValueError as e:
    pwd_err_field.write('<font color="red">Incorrect password for specified data file.</font>', unsafe_allow_html=True)

  # Remove error message/prompt on success
  if data is not None:
    st_error.empty()

  return data

  
def run():
  
  # Global configuration
  st.title('Growth Data Dashboard')

  # Ensure source data file can be loaded
  DATA = ensure_data_loaded()
  if DATA == None:
    return
  
  # Load growth chart data
  gc.init()
  who_weight_percentile_data = gc.get_percentile_lines(gc.GC_TYPE.WEIGHT_WHO, gc.SEX.M)
  who_weight_percentiles = pd.DataFrame(who_weight_percentile_data, index=[2,5,10,25,50,75,90,95,98]).transpose()
  
  st.line_chart(who_weight_percentiles)