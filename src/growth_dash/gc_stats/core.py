"""
General statistics functions
"""

import math

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
  return normsdist(Z)