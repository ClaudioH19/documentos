import openmeteo_requests   
import pandas as pd
import requests_cache
from retry_requests import retry
import json
import funciones_FAO56 as libfao56

# Función para obtener los datos diarios de Open-Meteo
def get_data_daily(lat, lon, z):
    # Configuración del cliente de Open-Meteo con caché y reintentos en caso de error
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Configuración de la solicitud a la API de Open-Meteo
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "start_date": "2017-01-01",
        "end_date": "2025-09-30",
        "daily": ["temperature_2m_max", "temperature_2m_min", "shortwave_radiation_sum", "et0_fao_evapotranspiration", "dew_point_2m_mean", "wind_speed_10m_mean", "relative_humidity_2m_mean","precipitation_sum"],
        "models": ["ecmwf_ifs"],
        "wind_speed_unit": "ms",
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    # Mostrar información sobre la ubicación
    print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

    # Procesar datos diarios
    daily = response.Daily()
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
    daily_shortwave_radiation_sum = daily.Variables(2).ValuesAsNumpy()
    daily_et0_fao_evapotranspiration = daily.Variables(3).ValuesAsNumpy()
    daily_dew_point_2m_mean = daily.Variables(4).ValuesAsNumpy()
    daily_wind_speed_10m_mean = daily.Variables(5).ValuesAsNumpy()
    daily_relative_humidity_2m_mean = daily.Variables(6).ValuesAsNumpy()
    daily_precipitation_sum = daily.Variables(7).ValuesAsNumpy()

    daily_data = {"date": pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    )}
    
    # Cálculos de FAO56 y otros parámetros
    albedo = 0.23  # albedo para cultivo de referencia (hierba)
    daily_data["lat"] = lat
    daily_data["lon"] = lon
    daily_data["z"] = z
    daily_data["source"] = "open-meteo_ecmwf_ifs"
    daily_data["granularity"] = "daily"
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["shortwave_radiation_sum"] = daily_shortwave_radiation_sum
    daily_data["et0_fao_evapotranspiration"] = daily_et0_fao_evapotranspiration
    daily_data["dew_point_2m_mean"] = daily_dew_point_2m_mean
    daily_data["wind_speed_10m_mean"] = daily_wind_speed_10m_mean
    daily_data["relative_humidity_2m_mean"] = daily_relative_humidity_2m_mean
    daily_data["precipitation_sum"] = daily_precipitation_sum
    
    # Cálculos FAO56 adicionales
    daily_data['tmean'] = libfao56.compute_tmean(daily_data["temperature_2m_min"], daily_data["temperature_2m_max"])
    daily_data['ea'] = libfao56.estimate_ea(daily_data["dew_point_2m_mean"])
    daily_data['u2'] = libfao56.conversion_wind_speed_2m(daily_data["wind_speed_10m_mean"], 10)
    daily_data['DOY'] = pd.DataFrame(index=daily_data['date']).index.dayofyear
    daily_data['Ra (MJ/m2dia)'] = libfao56.compute_ra(lat, daily_data['DOY'])
    daily_data['Rso (MJ/m2dia)'] = libfao56.compute_Rso(z, daily_data['Ra (MJ/m2dia)'])
    daily_data['Rnl'] = libfao56.compute_Rnl(daily_data['temperature_2m_min'], daily_data['temperature_2m_max'], daily_data['shortwave_radiation_sum'], daily_data['Rso (MJ/m2dia)'], daily_data['ea'])
    daily_data['Rsn (MJ/m2dia)'] = libfao56.compute_Rsnet_sw(daily_data['shortwave_radiation_sum'], albedo)
    daily_data['Rn (MJ/m2dia)'] = libfao56.compute_Rn(daily_data['Rsn (MJ/m2dia)'], daily_data['Rnl'])  
    daily_data['Eto'] = libfao56.compute_Eto(daily_data['Rn (MJ/m2dia)'], daily_data['temperature_2m_min'], daily_data['temperature_2m_max'], daily_data['tmean'], daily_data['u2'], z, daily_data['ea'], G=0)

    # Renombrar columnas y eliminar no necesarias
    rename_map = {
        "temperature_2m_max": "Tmax",
        "temperature_2m_min": "Tmin",
        "shortwave_radiation_sum": "Rs",
        "dew_point_2m_mean": "Tdwp",
        "wind_speed_10m_mean": "Wspeed2M",
        "relative_humidity_2m_mean": "RHmean",
        "precipitation_sum": "Precip_mm",
        "Rso (MJ/m2dia)": "Rso",
    }
    drop_cols = ["et0_fao_evapotranspiration", "tmean", "ea", "u2", "DOY", "Ra (MJ/m2dia)", "Rnl", "Rsn (MJ/m2dia)", "Rn (MJ/m2dia)"]

    daily_dataframe = pd.DataFrame(data=daily_data)
    daily_dataframe = daily_dataframe.rename(columns=rename_map)
    daily_dataframe = daily_dataframe.drop(columns=drop_cols)

    # Verificar si hay valores faltantes
    missing_flag = 0
    missing = daily_dataframe.isnull().sum()
    if missing.any():
        missing_flag = 1
        print("Warning: The following variables have missing values:")
        print(missing[missing > 0])
        missing_years = daily_dataframe[daily_dataframe.isnull().any(axis=1)].date.dt.year.unique()
        if len(missing_years) > 0:
            print("Warning: The following years have missing values:")
            print(missing_years)

    return daily_dataframe, missing_flag


# Cargar estaciones desde el archivo JSON
with open('estaciones.json') as f:
    data = json.load(f)
    estaciones = data["estaciones"]

# Iterar sobre las estaciones y procesar los datos
for estacion in estaciones:
    # Obtener los datos para cada estación
    df, missing_flag = get_data_daily(
        float(estacion['latitud']),
        float(estacion['longitud']),
        float(estacion['altura'])
    )

    # Verificar si hay valores faltantes
    if missing_flag:
        print(f"Advertencia: Datos faltantes detectados para la estación {estacion['comuna']}")

    # Guardar el DataFrame en un archivo CSV
    output_path = f"historical_data_maule/{estacion['comuna']}.csv"
    df.to_csv(output_path, index=False)
    print(f"Datos guardados en {output_path}")
    #wait random seconds to avoid overwhelming the API
    import time
    import random
    time.sleep(random.uniform(15, 30))
