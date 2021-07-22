import streamlit as st
import html
import base64
import pandas as pd
import altair as alt
from . import gc_stats as gc
from .data import load_data, transform

# Entire preprocessed source data set
DATA = None

def ensure_src_data_loaded():
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
  pwd_field=None
  # st_error = st.empty()
  # with st_error.beta_container():
  #   pwd_err_field = st.empty()
  #   pwd_field = st.text_input('Enter password:', pwd_qp or '', type='password')
  #   pwd_submit = st.button('Submit')
  
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
  # if data is not None:
  #   st_error.empty()

  return data
  
@st.cache
def get_wt_data(mrn):
  # Use mrn:mrn to slice, resulting in always getting a DataFrame, not a Series, even if only 1 data point
  return DATA.wt.loc[mrn:mrn]

@st.cache
def quantiles_per_month(data, quantiles):
  """
  Calculate the values at the given quantiles for each month of age in data.
  
  data - a dataframe with column 'Age' = age in months, and 'Val' = measurement
  quantiles - list of quantiles to calculate as % between 0-100 (e.g [25, 50, 75])
  """
  # Round ages to the nearest whole month
  month_bin = data['Age'].round()
  quantiles_by_month = {}
  for month in range(int(month_bin.max())+1):
    # Grab all weights (Val column) measured on month of age
    data_for_month = data.loc[month_bin==month, 'Val']
    
    # Calculate values at each percentile for this month
    quantiles_by_month[month] = [data_for_month.quantile(q / 100) for q in quantiles]
  
  # Convert {1: [3.0, 3.6, ...], 2: [...]} to DataFrame:
  #
  #      3   10   25  ...
  #   0: 1.7 2.2  ...
  #   1: 1.4 2.3  ...
  #   ...
  #
  return pd.DataFrame.from_dict(quantiles_by_month, orient='index', columns=['Agg' + str(q) for q in quantiles])
  
def run():
  global DATA

  # Global configuration
  title = 'Growth Data Dashboard'
  st.set_page_config(
    page_title=title,
    layout='wide')
  st.title(title)

  # Ensure source data file can be loaded. If not prompt for password.
  raw_src_data = ensure_src_data_loaded()
  if raw_src_data  is None:
    return
  
  # Preprocess data. Do this after from ensure_src_data_loaded to minimize UI state prompting for password.
  DATA = transform(raw_src_data)
  mrns = DATA.mrns
  wtdata = DATA.wt

  # Load growth chart data
  who_weight_m_percentiles = gc.get_percentile_lines(gc.GC_WEIGHT_WHO, gc.MALE)

  # Set up weight charts
  percentiles = ['3', '10', '25', '50', '75', '90', '97']
  line_colors = [
    ['3', '10', '25', '50', '75', '90', '97', 'Agg3', 'Agg50', 'Agg97'],
    ['palegoldenrod', 'palegoldenrod', 'palegoldenrod', 'palegoldenrod', 'palegoldenrod', 'palegoldenrod', 'palegoldenrod', 'lightblue', 'lightblue', 'lightblue']
  ]
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
    'color': alt.Color(                         # define multiple lines
      field='key',                              # - 'key' column created by transform_fold() above
      type='nominal',                           # - nominal = discrete unordered category
      legend=None,                              # - disable legend. we'll make our own labels directly on the lines using another chart.
      scale=alt.Scale(
        domain=line_colors[0],                  # map all percentile values to blue
        range=line_colors[1]))
  }
  gc_weight_m = (
    alt.Chart(who_weight_m_percentiles.reset_index())      # reset_index() converts row labels (age in months) to its own column
      .transform_fold(percentiles)                             # transform_fold: convert wide-form to long-form (altair-viz.github.io/user_guide/data.html#data-long-vs-wide)
                                       # eg. index 5   10  25         index key value
                                                #     1 mo  5.0 6.0 7.0   ->   1 mo  5   5.0
                                                #     2 mo  5.2 6.2 7.2        1 mo  10  6.0
                                                #                              1 mo  25  7.0
                                                #                              ...
      .mark_line()                                  # Make a line plot
      .encode(**weight_encoding))                                     # Configure chart visual (map visual properties to data columns, altair-viz.github.io/user_guide/encoding.html)
  
  # Build percentile lines for aggregate data
  agg_wt_quantiles = quantiles_per_month(wtdata, [3, 50, 97])

  ct_agg_wt = (
    alt.Chart(agg_wt_quantiles.reset_index())
      .transform_fold(['Agg3', 'Agg50', 'Agg97'])
      .mark_line()
      .encode(**weight_encoding))
    
  # Select specific patient's data
  st.sidebar.subheader('Available patients: ' + str(len(mrns)))
  mrn = st.sidebar.selectbox('MRN', mrns)
  ptwt = get_wt_data(mrn)
  
  # Plot patient's weight
  ct_ptwt = alt.Chart(
    ptwt
  ).mark_line(
    point=True
  ).encode(
    x='Age:Q',
    y='Val:Q',
    tooltip=['Age', 'Val']
  )

  # Sidebar
  st.sidebar.subheader('Reference Growth Percentiles')
  show_gc = st.sidebar.checkbox('WHO', value=True)
  show_agg = st.sidebar.checkbox('Craniofacial', value=True)
  
  # Combine selected graphs (order of addition determines z-order of lines)
  if show_gc and show_agg:
    ct = gc_weight_m + ct_agg_wt + ct_ptwt
  elif show_gc:
    ct = gc_weight_m + ct_ptwt
  elif show_agg:
    ct = ct_agg_wt + ct_ptwt
  else:
    ct = ct_ptwt

  # Main body
  st.header('Weight (WHO, Boys 0-2 years)')
  st.altair_chart(ct.interactive(), use_container_width=True)
  
  with st.beta_expander('Show Patient Data'):
    if len(ptwt) > 0:
      col1, col2, _ = st.beta_columns(3)
      col1.write('MRN: ' + str(mrn))
      col2.write('DOB: ' + ptwt.iloc[0]['DOB'].strftime('%D'))
      st.write(ptwt[['Age', 'Val', 'TS']])