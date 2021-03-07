import os
import json
import pandas as pd

from .constants import *
from .core import *

# Master LMS data for all growth chart types
GC_DATA = None

# Location of this source file and data file
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
GCCURVEDATA_FILE = os.path.join(__location__, 'GCCurveData.json')

# =========================================================================
# Functions to convert LMS parameters <-> values at specific percentiles.
# These functions must be given an LMS lookup table.
# =========================================================================
def get_lms_table(gc_type, sex):
  """
  Given a growth chart type, gc_type, and sex, return the appropriate LMS
  lookup table from GC_DATA, loaded from GCCurveData.json
  """
  if (gc_type not in GC_DATA) or (sex not in GC_DATA[gc_type]['data']):
    return None
  
  return GC_DATA[gc_type]['data'][sex]

def get_lms_for_x(LMS_table, x):
  """
  Given the LMS_table table of LMS parameters, in the format:
    
    [
      {'x': 23, 'L': 0.0, 'M': 0.0, 'S': 0.0},
      {'x': 24, 'L': 1.0, 'M': 2.0, 'S': 3.0},
      ...
    ]
  
  Where x is usually the age in months, except for weight-for-length, where x is length,
  
  Return LMS parameters for arbitrary x value by interpolating data points.
  
  Return value only contains the LMS values. Using the table above, for x=23.5
  
    { 'L': 0.5, 'M': 1.0, 'S', 1.5 }
  
  Returns None if x is beyond bounds of table (e.g. x < youngest age or x > oldest age)
    
  """

  n = len(LMS_table)

  for i in range(0, n):
    if x == LMS_table[i]['x']:
      # Return exact age matches
      return {
        'L': LMS_table[i]['L'],
        'M': LMS_table[i]['M'],
        'S': LMS_table[i]['S']
      }
    elif (i < n-1) and (x > LMS_table[i]['x']) and (x <= LMS_table[i+1]['x']):
      # If we are in between data points, interpolate neighboring LMS parameters
      weight = (x - LMS_table[i]['x']) / (LMS_table[i+1]['x'] - LMS_table[i]['x'])
      return {
        'L': weighted_avg(LMS_table[i]['L'], LMS_table[i+1]['L'], weight),
        'M': weighted_avg(LMS_table[i]['M'], LMS_table[i+1]['M'], weight),
        'S': weighted_avg(LMS_table[i]['S'], LMS_table[i+1]['S'], weight)
      }

  return None

def lms_to_percentiles(LMS_table, percentiles):
  """
  Convert:
 
   [{"x": 23, L: 0.0, M: 0.0, S: 0.0},
    {"x": 24, L: ...},
    ...],
   [5, 10, ...]
 
  To a pandas data frame with a column for each desired percentile:
 
               5           10             15       ...
     23: value at 5%,  value at 10%, value at 15%, ...
     24: ...,
   }
  """
  
  # Iterate over row in LMS table (each row contains LMS params at a given age), change:
  #   {"x": 23, L: 0.0, M: 0.0, S: 0.0},
  #     to
  #   {23: [val-at-5%, val-at-10%, ...]}
  rows = {
    row['x']: [percentile_to_x(p, row['L'], row['M'], row['S']) for p in percentiles]
    for row in LMS_table
  }
  
  # Convert to pandas data frame:
  # - orient='index' to treat each key in rows as a row, not column
  # - use percentiles as the column names
  return pd.DataFrame.from_dict(rows, orient='index', columns=percentiles)

_percentile_cache = {}
def load_percentile_cache(gc_data, gc_types):
  """
  Precalculate and cache percentile curves for a list of growth chart types, gc_types
  """
  for gc_type in gc_types:
    _percentile_cache[gc_type] = {
      MALE: lms_to_percentiles(gc_data[gc_type]['data'][MALE], DEFAULT_PERCENTILES),
      FEMALE: lms_to_percentiles(gc_data[gc_type]['data'][FEMALE], DEFAULT_PERCENTILES)
    }

# =========================================================================
# Public interface
# =========================================================================
def init():
  """
  Called by __init__.py to initialize module.

  Load LMS data sets from file and preprocess.
  """
  global GC_DATA
  if GC_DATA is not None:
    return
  
  with open(GCCURVEDATA_FILE, 'r') as f:
    GC_DATA = json.load(f)
  
  # Precalculate default percentiles for the most common growth charts
  load_percentile_cache(GC_DATA, [
    GC_WEIGHT_WHO, GC_HEIGHT_WHO, GC_WFL_WHO])
  
  return GC_DATA

def get_percentile_lines(gc_type, sex, percentiles=DEFAULT_PERCENTILES):
  """
  Return percentile lines for a given growth chart type and sex.
  
  Return value is a pandas data frame with a column for each percentile:
 
               5           10             15        ...
     age: value at 5%,  value at 10%, value at 15%, ...
  
  Example:
  
    Get the 5th, 25th, 50th, 75th and 95th percentile weight lines for boys 0-24 months:
  
      gc_stats.get_percentile_lines(gc_stats.GC_WHO_WEIGHT, gc_stats.MALE, [5,25,50,75,95])
  """
  LMS_table = get_lms_table(gc_type, sex)
  if LMS_table is None:
    return {}
  
  # If percentile lines were precalculated for this chart type, return that copy
  if (percentiles == DEFAULT_PERCENTILES) and (gc_type in _percentile_cache):
    return _percentile_cache[gc_type][sex]
  
  return lms_to_percentiles(LMS_table, percentiles)

def percentile(gc_type, sex, x, val):
  """
  Return the percentile of a given value on a growth chart
  
  x is usually the age in months. For weight-for-length, x is length.
  """
  LMS_table = get_lms_table(gc_type, sex)
  if LMS_table is None:
    return None

  LMS = get_lms_for_x(LMS_table, x)
  return x_to_percentile(val, LMS['L'], LMS['M'], LMS['S'])

def zscore(gc_type, sex, x, val):
  """
  Return the z-score of a given value on a growth chart

  x is usually the age in months. For weight-for-length, x is length.
  """
  LMS_table = get_lms_table(gc_type, sex)
  if LMS_table is None:
    return None

  LMS = get_lms_for_x(LMS_table, x)
  return x_to_zscore(val, LMS['L'], LMS['M'], LMS['S'])