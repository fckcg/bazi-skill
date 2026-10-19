"""Meeus/NOAA Julian-century equation of time; still an approximate solar model."""
from datetime import timezone
import math

MODEL = 'noaa-meeus-julian-v1'
SOURCE = 'https://gml.noaa.gov/grad/solcalc/calcdetails.html'


def equation_of_time(dt):
    if dt.utcoffset() is None:
        raise ValueError('Equation of time requires an aware UTC instant.')
    utc = dt.astimezone(timezone.utc)
    jd = (utc.timestamp()/86400) + 2440587.5
    t = (jd-2451545.0)/36525
    l0 = math.radians((280.46646+t*(36000.76983+0.0003032*t)) % 360)
    m = math.radians(357.52911+t*(35999.05029-0.0001537*t))
    ecc = 0.016708634-t*(0.000042037+0.0000001267*t)
    eps = 23+(26+(21.448-t*(46.815+t*(0.00059-t*0.001813)))/60)/60
    eps += 0.00256*math.cos(math.radians(125.04-1934.136*t))
    y = math.tan(math.radians(eps)/2)**2
    e = (y*math.sin(2*l0)-2*ecc*math.sin(m)+4*ecc*y*math.sin(m)*math.cos(2*l0)
         -0.5*y*y*math.sin(4*l0)-1.25*ecc*ecc*math.sin(2*m))
    return 4*math.degrees(e)
