import streamlit as st
from .data import load_data

def run():
  st.title('Growth Data Dashboard')
  
  # Data source passed in as query param (https://.../?src=)
  params = st.experimental_get_query_params()
  data = load_data(params['src'][0], params['pwd'][0])
  
  st.write(data)