import numpy as np
import pandas as pd

### FAO-56 ###

#Constantes

lambdaa = 2.45  # calor latente de vaporización MJ/kg (en T normales)



def compute_P_kPa(z):
    """
    Calcula la presión atmosférica en función de la elevación sobre el nivel del mar.

    Parámetros:
        elevacion (float): Elevación sobre el nivel del mar en metros.

    Retorna:
        float: Presión atmosférica en kPa.
    """
    P = 101.3 * ((293 - 0.0065 * z) / 293) ** 5.26
    return P

def compute_psicrometrica(P):
    """
    Calcula la constante psicrométrica.

    Parámetros:
        P (float): Presión atmosférica en kPa.

    Retorna:
        float: valor medio psicrométrica en kPa/°C.
    """
    gamma = 0.000665 * P # ese valor es contante apsi
    return gamma

def compute_tmean(tmin, tmax):
    tmean = (tmin + tmax) / 2
    return tmean

def compute_e0(t):
    """
    Calcula la presión de vapor de saturación (e0) en kPa a partir de la temperatura.

    Parámetros:
        t (float): Temperatura en °C.

    Retorna:
        float: Presión de vapor de saturación en kPa.
    """
    e0 = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
    return e0

def compute_es(tmin, tmax):
    """
    Calcula la presión de vapor de saturación media (es) en kPa.

    Parámetros:
        tmin (float): Temperatura mínima diaria en °C.
        tmax (float): Temperatura máxima diaria en °C.

    Retorna:
        float: Presión de vapor de saturación media en kPa.
    """
    es_tmin = compute_e0(tmin)
    es_tmax = compute_e0(tmax)
    es = (es_tmin + es_tmax) / 2
    return es

def compute_delta(tmean):
    """
    Calcula la pendiente de la curva de presión de vapor de saturación (delta) en kPa/°C.

    Parámetros:
        tmean (float): Temperatura media diaria en °C.
    """
    delta = (4098 * compute_e0(tmean)) / (((tmean + 237.3) ** 2))
    return delta


def compute_ea_by_hrminmax(tmin, tmax, rhmin,rhmax):

    ea= (compute_e0(tmin) * (rhmax / 100) + compute_e0(tmax) * (rhmin / 100))/2
    return ea

def compute_ea_by_hrmax(tmin, rhmax):
    ea = compute_e0(tmin) * (rhmax / 100)
    return ea

def compute_ea_by_hrmean(tmean, rhmean):
    ea = compute_e0(tmean) * (rhmean / 100)
    return ea

def estimate_ea(tdewpoint):
    #solo tmin como aprox si ocurre al amanecer
    ea = compute_e0(tdewpoint)
    return ea


def compute_deficit_vapor(e0, ea):
    vpd = e0 - ea
    return vpd

def compute_evaporacion_equivalente(rn):
    """
    Convierte la radiación neta (Rn) de MJ/m²/día a mm/día.

    Parámetros:
        rn (float): Radiación neta en MJ/m²/día.

    Retorna:
        float: Evaporación equivalente en mm/día.
    """
    evap_equiv = rn / lambdaa
    return evap_equiv

def compute_G_daily():
    """
    Asume que el flujo de calor del suelo diario (G) es cero para periodos diarios.
    """
    return 0

def compute_G_monthly(tmean_series):
    """
    Calcula el flujo de calor del suelo mensual (G)
    desconociendo Tmes,i+1

    """
    tmean_series = pd.Series(tmean_series)
    G_monthly = tmean_series.diff().shift(-1) * 0.14 # (i - i-1)
    return G_monthly

def compute_G_hourly(rn, daytime):
    if daytime:
        G_hourly = 0.1 * rn
    else:
        G_hourly = 0.5 * rn
    return G_hourly

def conversion_wind_speed_2m(u_z, z):

    # Aplicando la ley de potencia para la corrección de altura
    u_2m = u_z * (4.87 / np.log(67.8 * z - 5.42))
    return u_2m

def conversor_WWm2dia_a_MJJm2dia(rs_wm2d):

    return rs_wm2d * 0.0864  # 1 W/m² = 0.0864 MJ/m²/día

def compute_Rsnet_sw(rs, albedo):
    return rs * (1 - albedo)

def compute_Rn(rsnet_sw, rlnet_lw):
    return rsnet_sw - rlnet_lw

def compute_Rso( z, ra):
    # Ra en MJ/m²/día
    # Rso = (0.75 + 2e-5 * z) * Ra
    Rso = (0.75 + (2e-5 * z)) * ra
    return Rso

def compute_Eto(rn,tmin,tmax,tmean,u2,z,ea,G):

    delta = compute_delta(tmean)
    gamma = compute_psicrometrica(compute_P_kPa(z))
    
    es= compute_es(tmean,tmean)
    #es = compute_es(tmin,tmax)
    numerator = 0.408 * delta * (rn - G) + gamma * (900 / (tmean + 273)) * u2 * (es - ea)
    denominator = delta + gamma * (1 + 0.34 * u2)
    eto = numerator / denominator
    return eto


import math
from datetime import datetime

def compute_ra(lat_deg, fecha):
    """
    Calcula la radiación extraterrestre Ra [MJ/m²/día] de forma vectorizada.
    lat_deg: float (latitud en grados)
    fecha: int o array-like (día juliano del año)
    """

    J = np.asarray(fecha, dtype=float)
    Gsc = 0.082  # MJ m^-2 min^-1
    phi = np.radians(lat_deg)
    dr = 1 + 0.033 * np.cos((2 * np.pi / 365) * J)
    delta = 0.409 * np.sin((2 * np.pi / 365) * J - 1.39)
    arg = -np.tan(phi) * np.tan(delta)
    arg = np.clip(arg, -1, 1)
    omega_s = np.arccos(arg)
    Ra = (24 * 60 / np.pi) * Gsc * dr * (
        omega_s * np.sin(phi) * np.sin(delta)
        + np.cos(phi) * np.cos(delta) * np.sin(omega_s)
    )

    return Ra


def compute_relative_humidity(tmean, ea):
    e0 = compute_e0(tmean)
    hr = (ea / e0) * 100 
    return hr

def compute_Rnl(tmin,tmax,rs,rso,ea):
    """
    Calcula la radiación neta de onda larga (Rnl) en MJ/m²/día.
    tmin: float o array-like (temperatura mínima en °C)
    tmax: float o array-like (temperatura máxima en °C)
    rs: float o array-like (radiación solar global en MJ/m²/día)
    rso: float o array-like (radiación solar clara en MJ/m²/día)
    """
    sigma = 4.903e-9  # Constante de Stefan-Boltzmann en MJ K^-4 m^-2 día^-1
    tmin_k = np.asarray(tmin, dtype=float) + 273.16
    tmax_k = np.asarray(tmax, dtype=float) + 273.16
    rs = np.asarray(rs, dtype=float)
    rso = np.asarray(rso, dtype=float)

    # Evitar división por cero
    rso = np.where(rso == 0, np.nan, rso)

    rnl = sigma * ((tmax_k ** 4 + tmin_k ** 4) / 2) * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * (rs / rso) - 0.35)
    return rnl