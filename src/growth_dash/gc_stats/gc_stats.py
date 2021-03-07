import os
import math
import json
import pprint

# Location of this source file and data file
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
GCCURVEDATA_FILE = os.path.join(__location__, 'GCCurveData.json')

# =========================================================================
# General statistics functions
# =========================================================================
def weighted_avg(a, b, weight):
  """
  Find number between a and b at fractional distance given by weight between [0, 1].
  """
  return b * weight + a * (1 - weight)

def erf(x):
  """
  Error function implementation derived from codeproject.com/Articles/408214/Excel-Function-NORMSDIST-z
  
  If Y is normally distributed with mean=0 and variance=1/2 => erf(x) is probability that Y falls in [-x, x].
  """

  # Constants for A&S formula 7.1.26
  a1 =  0.254829592
  a2 = -0.284496736
  a3 =  1.421413741
  a4 = -1.453152027
  a5 =  1.061405429
  p  =  0.3275911
  t = 1.0/(1.0 + p*abs(x))

  # Approximation using Horner's method. Takes O(n) operations for nth order polynomial.
  return 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1) * t * math.exp(-x*x)

def normsinv(p):
  """
  Normal distribution percentile to Z-score
    
    normsinv: (0,1) -> (-inf,+inf)
  
  Ported from JS library by Peter John Acklam (home.online.no/~pjacklam), timestamp 2003-05-05 05:15:14
  
  Lower tail quantile for standard normal distribution function.
  
  This function returns an approximation of the inverse cumulative
  standard normal distribution function.  I.e., given P, it returns
  an approximation to the X satisfying P = Pr{Z <= X} where Z is a
  random variable from the standard normal distribution.
  
  The algorithm uses a minimax approximation by rational functions
  and the result has a relative error whose absolute value is less
  than 1.15e-9.

  An algorithm with a relative error less than 1.15*10-9 in the entire region.
  """

  # Coefficients in rational approximations
  a = [-3.969683028665376e+01, 2.209460984245205e+02,
    -2.759285104469687e+02, 1.383577518672690e+02,
    -3.066479806614716e+01, 2.506628277459239e+00]

  b = [-5.447609879822406e+01, 1.615858368580409e+02,
    -1.556989798598866e+02, 6.680131188771972e+01,
    -1.328068155288572e+01]

  c = [-7.784894002430293e-03, -3.223964580411365e-01,
    -2.400758277161838e+00, -2.549732539343734e+00,
    4.374664141464968e+00, 2.938163982698783e+00]

  d = [7.784695709041462e-03, 3.224671290700398e-01,
    2.445134137142996e+00, 3.754408661907416e+00]

  # Define break-points.
  plow = 0.02425
  phigh = 1 - plow

  # Rational approximation for lower region:
  if (p < plow):
    q = math.sqrt(-2 * math.log(p))
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)

  # Rational approximation for upper region:
  if (phigh < p):
    q = math.sqrt(-2 * math.log(1 - p))
    return  - (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)

  # Rational approximation for central region:
  q = p - 0.5
  r = q * q
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)

def normsdist(z):
  """
  Normal distribution Z-score to percentile

    normsdist: (-inf,+inf) -> (0,1)
    
  Return probability that the observed value of a standard normal random variable will be less than or equal to z.
    
  Derived from codeproject.com/Articles/408214/Excel-Function-NORMSDIST-z
  """
  sign = z / abs(z)
  return 0.5 * (1.0 + sign * Math.erf(abs(z)/Math.sqrt(2)))

def zscore_to_x(Z, L, M, S):
  """
  Adapted from Nikolai Schwertner, MedAppTech (2012-11-28)
  
  From CDC (http://www.cdc.gov/growthcharts/percentile_data_files.htm):
  
  The LMS parameters are the median (M), the generalized coefficient of
  variation (S), and the power in the Box-Cox transformation (L).
  
  To obtain the z-score (Z) and corresponding percentile for a given
  measurement (X), use the following equation:
  
    Z = (((X/M)**L) - 1)/LS  , L<>0
    Z = ln(X/M)/S            , L=0
  """

  if L != 0:
    return M * math.pow(1 + L * S * Z, 1 / L)
  else:
    return M * Math.exp(S * Z)

def x_to_zscore(x, L, M, S):
  """
  Adapted from Nikolai Schwertner, MedAppTech (2012-11-28)
  
  From CDC (http://www.cdc.gov/growthcharts/percentile_data_files.htm):
  
  The LMS parameters are the median (M), the generalized coefficient of
  variation (S), and the power in the Box-Cox transformation (L).

  To obtain the value (X) of a given physical measurement at a
  particular z-score or percentile, use the following equation:
  
    X = M (1 + LSZ)**(1/L), L <> 0
    X = M exp(SZ), L = 0
  """

  if L != 0:
    return (Math.pow(X/M, L) - 1) / (L * S)
  else:
    return Math.log(X/M) / S

def percentile_to_x(percentile, L, M, S):
  """
  Given a percentile between [0, 100] and corresponding LMS paramters, return the actual expected data value.
  """
  
  Z = normsinv(percentile/100)
  return zscore_to_x(Z, L, M, S)

def x_to_percentile(x, L, M, S):
  Z = x_to_zscore(x, L, M, S)
  return normsdist(Z);

# =========================================================================
# Functions to convert LMS parameters <-> values at specific percentiles.
# These functions must be given an LMS lookup table based on age.
# =========================================================================
def get_lms_for_age(LMS_by_age, age_in_months):
  """
  Given the LMS_by_age table of LMS parameters for months of age, in the format:
    
    [
      {'Agemos': 23, 'L': 0.0, 'M': 0.0, 'S': 0.0},
      ...
    ]
  
  Return the LMS parameters for any decimal age, age_in_months, by interpolating data points
  in the table, in the format:
  
    {'Agemos': age_in_months, 'L': 0.0, 'M': 0.0, 'S', 0.0}
    
  """

  n = len(LMS_by_age)

  for i in range(0, n):
    if age_in_months == LMS_by_age[i]['Agemos']:
      # Return exact age matches
      return {
        'L': LMS_by_age[i]['L'],
        'M': LMS_by_age[i]['M'],
        'S': LMS_by_age[i]['S']
      }
    elif (i < n-1) and (age_in_months > LMS_by_age[i]['Agemos']) and (age_in_months <= LMS_by_age[i+1]['Agemos']):
      # If we are in between data points, interpolate neighboring LMS parameters
      weight = (age_in_months - LMS_by_age[i]['Agemos']) / (LMS_by_age[i+1]['Agemos'] - LMS_by_age[i]['Agemos'])
      return {
        'L': weighted_avg(LMS_by_age[i]['L'], LMS_by_age[i+1]['L'], weight),
        'M': weighted_avg(LMS_by_age[i]['M'], LMS_by_age[i+1]['M'], weight),
        'S': weighted_avg(LMS_by_age[i]['S'], LMS_by_age[i+1]['S'], weight)
      }

  return None

def lms_to_percentiles(LMS_by_age, percentiles):
  """
  Convert:
 
   [{"Agemos": 23, L: 0.0, M: 0.0, S: 0.0},
    {"Agemos": 24, L: ...},
    ...],
   [5, 10, ...]
 
  To a table with age and specific values at desired percentiles:
 
   {
     23: [value at 5%, value at 10%, ...],
     24: [...],
   }
  """
  
  # Iterate over row in LMS table (each row contains LMS params at a given age), change:
  #   {"Agemos": 23, L: 0.0, M: 0.0, S: 0.0},
  #     to
  #   {23: [val-at-5%, val-at-10%, ...]}
  return {
    row['Agemos']: [percentile_to_x(p, row['L'], row['M'], row['S']) for p in percentiles]
    for row in LMS_by_age
  }

CACHED_PERCENTILES = [2,5,10,25,50,75,90,95,98]
_percentile_cache = {}
def load_percentile_cache(gc_data, gc_types):
  for gc_type in gc_types:
    _percentile_cache[gc_type] = {
      SEX.M: lms_to_percentiles(gc_data[gc_type]['data'][SEX.M], CACHED_PERCENTILES),
      SEX.F: lms_to_percentiles(gc_data[gc_type]['data'][SEX.F], CACHED_PERCENTILES)
    }

# =========================================================================
# Public interface
# =========================================================================
class GC_TYPE:
  """
  Available growth chart types constants to be used as gc_type parameter
  """
  HEIGHT_OLSEN='OLSEN_LENGTH'
  HEIGHT_FENTON='FENTON_LENGTH'
  HEIGHT_WHO='WHO_LENGTH'
  HEIGHT_CDC='CDC_STATURE'
  WEIGHT_OLSEN='OLSEN_WEIGHT'
  WEIGHT_FENTON='FENTON_WEIGHT'
  WEIGHT_WHO='WHO_WEIGHT'
  WEIGHT_CDC='CDC_WEIGHT'
  HC_OLSEN='OLSEN_HEADC'
  HC_FENTON='FENTON_HEADC'
  HC_WHO='WHO_HEADC'
  HC_CDC='CDC_HEADC'
  BMI_FENTON='FENTON_BMI'
  BMI_WHO='WHO_BMI'
  BMI_CDC='CDC_BMI'

class SEX:
  M='male'
  F='female'
  
# Master LMS data for all growth chart types
GC_DATA = None

def init():
  """
  Load LMS data sets from file and preprocess
  """
  global GC_DATA
  if GC_DATA is not None:
    return
  
  with open(GCCURVEDATA_FILE, 'r') as f:
    GC_DATA = json.load(f)
  
  # Precalculate default percentiles for the most common growth charts
  load_percentile_cache(GC_DATA, [
    GC_TYPE.HEIGHT_FENTON, GC_TYPE.HEIGHT_WHO, GC_TYPE.HEIGHT_CDC,
    GC_TYPE.WEIGHT_FENTON, GC_TYPE.WEIGHT_WHO, GC_TYPE.WEIGHT_CDC,
    GC_TYPE.HC_FENTON, GC_TYPE.HC_WHO, GC_TYPE.HC_CDC])
  
  return GC_DATA

def _get_lms_table(gc_type, sex):
  if (gc_type not in GC_DATA) or (sex not in GC_DATA[gc_type]['data']):
    return None
  
  return GC_DATA[gc_type]['data'][sex]
  

def get_percentile_lines(gc_type, sex, percentiles=CACHED_PERCENTILES):
  """
  Return percentile lines for a given growth chart type and sex.
  Default percentiles are precalculated.
  """
  LMS_by_age = _get_lms_table(gc_type, sex)
  if LMS_by_age is None:
    return {}
  
  # If percentile lines precalculated, return that copy
  if (percentiles == CACHED_PERCENTILES) and (gc_type in _percentile_cache):
    return _percentile_cache[gc_type][sex]
  
  return lms_to_percentiles(LMS_by_age, percentiles)

def percentile(gc_type, sex, age_in_months, val):
  """
  Return the percentile of a given value on a growth chart, -1 if error
  """
  LMS_by_age = _get_lms_table(gc_type, sex)
  if LMS_by_age is None:
    return None

  LMS = get_lms_for_age(LMS_by_age, age_in_months)
  return x_to_percentile(val, **LMS)

def zscore(gc_type, sex, val):
  """
  Return the z-score of a given value on a growth chart
  """
  LMS_by_age = _get_lms_table(gc_type, sex)
  if LMS_by_age is None:
    return None

  LMS = get_lms_for_age(LMS_by_age, age_in_months)
  return x_to_zscore(val, **LMS)

__all__ = [GC_TYPE, SEX, init, get_percentile_lines, percentile, zscore]