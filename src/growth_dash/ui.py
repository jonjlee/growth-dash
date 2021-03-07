import streamlit as st
import html
import base64
import pandas as pd
import altair as alt
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
  if DATA is None:
    return
  
  # Load growth chart data
  who_weight_m_percentiles = gc.get_percentile_lines(gc.GC_WEIGHT_WHO, gc.MALE)
  who_weight_f_percentiles = gc.get_percentile_lines(gc.GC_WEIGHT_WHO, gc.FEMALE)
  who_height_m_percentiles = gc.get_percentile_lines(gc.GC_HEIGHT_WHO, gc.MALE)
  who_height_f_percentiles = gc.get_percentile_lines(gc.GC_HEIGHT_WHO, gc.FEMALE)
  who_wfl_m_percentiles = gc.get_percentile_lines(gc.GC_WFL_WHO, gc.MALE)
  who_wfl_f_percentiles = gc.get_percentile_lines(gc.GC_WFL_WHO, gc.FEMALE)
  
  # Set up weight charts
  percentiles = ['3', '10', '25', '50', '75', '90', '97']
  weight_encoding = {
    'x': alt.X(
      field='index',                            # 'index' column created by reset_index() above
      type='quantitative',                      # quantitative = continuous real value (altair-viz.github.io/user_guide/encoding.html#encoding-data-types)
      axis=alt.Axis(
        title='Age (months)')),
    'y': alt.Y(
      field='value',                            # 'value' column created by transform_fold() above
      type='quantitative',
      axis=alt.Axis(title='Weight (kg)')),
    'color': alt.Color(                            # define colors for the multiple lines
      field='key',                              # 'key' column created by transform_fold() above
      type='nominal',                           # nominal = discrete unordered category
      legend=alt.Legend(                        # temporary legend config with text-only - no title, no lines, labels moved a few pixels left
        title=None,                             # TODO: use mark_text() to properly position labels on lines directly
        symbolSize=0,
        labelOffset=-10,
        values=percentiles[::-1]),
      scale=alt.Scale(
        domain=percentiles,                     # map all percentile values to blue
        range=['lightblue']*len(percentiles)))
  }
  
  ct_weight_m=alt.Chart(
    who_weight_m_percentiles.reset_index()      # reset_index() converts row labels (age in months) to its own column
  ).transform_fold(                             # transform_fold: convert wide-form to long-form (altair-viz.github.io/user_guide/data.html#data-long-vs-wide)
    percentiles                                 # eg. index 5   10  25         index key value
                                                #     1 mo  5.0 6.0 7.0   ->   1 mo  5   5.0
                                                #     2 mo  5.2 6.2 7.2        1 mo  10  6.0
                                                #                              1 mo  25  7.0
                                                #                              ...
  ).mark_line(                                  # Make a line plot
  ).encode(                                     # Configure chart visual (map visual properties to data columns, altair-viz.github.io/user_guide/encoding.html)
    **weight_encoding
  )
    
  ct_weight_f=alt.Chart(
    who_weight_f_percentiles.reset_index()
  ).transform_fold(
    percentiles
  ).mark_line(
  ).encode(
    **weight_encoding
  )
  
  # Build list of patients
  mrns = DATA['MRN'].unique()
  mrns.sort()
  mrn = st.sidebar.selectbox('MRN', mrns)
  
  # Select specific patient's data
  ptdata = DATA.loc[DATA['MRN']==mrn]
  
  st.header('Weight (Boys 0-2 years)')
  st.altair_chart(ct_weight_m, use_container_width=True)
  
  st.write(ptdata)