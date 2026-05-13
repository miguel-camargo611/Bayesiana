"""
build_presence_only_dataset.py
==============================
Construye el dataset final para el modelo Bayesiano de Presencia-Only
(Metodología Golini) a partir de:
    - Datos de presencia de GBIF (copeton_gbif.csv)
    - Datos de contaminación horaria de RMCAB (bogota_pollution_hourly.csv)
    - Coordenadas de estaciones de monitoreo (bogota_stations_coords.csv)

Salida: data/processed/copeton_presence_only_ready.csv

Pasos:
    1. Cargar y filtrar presencias GBIF (Bogotá, 2022-2026)
    2. Aplicar spatial thinning (1 registro por celda ~500m)
    3. Generar puntos de fondo (background/quadrature points) con grilla espacial
    4. Preprocesar datos de contaminación (pivotar, limpiar, UTC→BOG)
    5. Merge espaciotemporal: punto → estación más cercana + fecha + hora
    6. Ensamblar dataset final con columna 'y' y 'quadrature_weight'

Referencia metodológica: Golini (2013) PhD Thesis; Renner & Warton (2013)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# ─────────────────────────────────────────
# CONFIGURACIÓN DE RUTAS
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GBIF_FILE       = os.path.join(BASE_DIR, 'NUEVO', 'copeton_gbif.csv')
POLLUTION_FILE  = os.path.join(BASE_DIR, 'data', 'raw', 'bogota_pollution_hourly.csv')
STATIONS_FILE   = os.path.join(BASE_DIR, 'data', 'raw', 'bogota_stations_coords.csv')
OUTPUT_FILE     = os.path.join(BASE_DIR, 'data', 'processed', 'copeton_presence_only_ready.csv')

# ─────────────────────────────────────────
# PARÁMETROS DEL MODELO
# ─────────────────────────────────────────
# Bounding box de Bogotá (Ampliado para incluir Usme y Usaquén, pero sin rural)
BOGOTA_LAT_MIN, BOGOTA_LAT_MAX = 4.48, 4.82
BOGOTA_LON_MIN, BOGOTA_LON_MAX = -74.22, -74.01

# Período de análisis - incluye 2021 donde la mayoria de estaciones RMCAB tienen datos
YEAR_MIN, YEAR_MAX = 2021, 2026

# Spatial thinning: tamaño de celda en grados (~500m ≈ 0.0045°)
THINNING_CELL_SIZE = 0.005  # ~550m en el ecuador (~0.0045 grados)

# Background points: grilla espacial regular
BACKGROUND_CELL_SIZE = 0.008  # ~880m — menos denso que las presencias
MAX_DISTANCE_KM = 20.0       # Descartar matches a más de 20km de una estación

# Ratio de fondo: usamos todos los puntos de grilla que tengan match de contaminación
BACKGROUND_RATIO = 2         # Intentar ~2x el número de presencias filtradas


# ─────────────────────────────────────────
# FUNCIONES UTILITARIAS
# ─────────────────────────────────────────
def is_strictly_urban(lat, lon):
    """
    Define fronteras diagonales para mantener exclusivamente el área urbana:
    - Excluye Cerros Orientales (este)
    - Excluye Sabana de Occidente: Cota, Funza, Mosquera (oeste)
    - Excluye zona sur-occidente: Sibaté, rural Soacha, Quiba, Mochuelo (suroeste)
    """
    # Frontera oriental (Cerros)
    border_lon_east = np.where(lat < 4.60, 
                          0.507 * (lat - 4.531) - 74.100, 
                          0.363 * (lat - 4.600) - 74.065)
                          
    # Frontera occidental (Río Bogotá aprox)
    border_lon_west = 0.555 * (lat - 4.67) - 74.140
    
    # Frontera suroccidental (Línea roja hacia Sibaté/Quiba)
    border_lon_sw = -0.875 * (lat - 4.48) - 74.120
    
    return (lon <= border_lon_east) & (lon >= border_lon_west) & (lon >= border_lon_sw)
def haversine(lat1, lon1, lat2, lon2):
    """Distancia haversine en km entre dos puntos geográficos."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def assign_nearest_station(df_points, df_stations):
    """
    Para cada punto en df_points, encuentra la estación más cercana en df_stations.
    Requiere columnas 'lat'/'lon' en df_points y 'lat'/'lon'/'station_name' en df_stations.
    Retorna df_points con columnas: nearest_station, distance_km
    """
    print(f"  Calculando estación más cercana para {len(df_points):,} puntos...")
    # Coordenadas de estaciones como arrays numpy
    s_lat = df_stations['lat'].values.astype(float)
    s_lon = df_stations['lon'].values.astype(float)
    s_name = df_stations['station_name'].values

    # Filtrar estaciones con coordenadas válidas de Bogotá
    # Nota: Guaymaral, Suba, Tunal, Usaquen tienen coords correctas; las otras 6 tienen
    # coords erroneas en el CSV fuente (valores europeos) y son excluidas automaticamente
    valid_mask = (s_lat >= 4.4) & (s_lat <= 4.9) & (s_lon >= -74.35) & (s_lon <= -73.9)
    s_lat = s_lat[valid_mask]
    s_lon = s_lon[valid_mask]
    s_name = s_name[valid_mask]
    print(f"  Usando {len(s_name)} estaciones válidas en Bogotá.")

    nearest_names = []
    nearest_dists = []

    p_lat = df_points['lat'].values.astype(float)
    p_lon = df_points['lon'].values.astype(float)

    for i in range(len(p_lat)):
        dists = haversine(p_lat[i], p_lon[i], s_lat, s_lon)
        idx = np.argmin(dists)
        nearest_names.append(s_name[idx])
        nearest_dists.append(dists[idx])

    df_points = df_points.copy()
    df_points['nearest_station'] = nearest_names
    df_points['distance_km'] = nearest_dists
    return df_points


def round_to_hour(hour_val, minute_val=0):
    """Redondea al bloque de hora más cercano."""
    if minute_val >= 30:
        return (int(hour_val) + 1) % 24
    return int(hour_val)


def parse_gbif_eventdate(date_str):
    """
    Parsea el campo eventDate de GBIF que puede venir en múltiples formatos:
    - '2023-06-16'
    - '2023-06-16T14:30'
    - '2023-06-16T14:30:00Z'
    Retorna (date_str_YYYY-MM-DD, hour_int_or_nan)
    """
    if pd.isna(date_str) or date_str == '':
        return None, np.nan
    date_str = str(date_str).strip()
    try:
        if 'T' in date_str or ' ' in date_str:
            sep = 'T' if 'T' in date_str else ' '
            parts = date_str.split(sep)
            date_part = parts[0]
            time_part = parts[1].replace('Z', '').split('+')[0]
            time_bits = time_part.split(':')
            hour = int(time_bits[0])
            minute = int(time_bits[1]) if len(time_bits) > 1 else 0
            return date_part, round_to_hour(hour, minute)
        else:
            return date_str, np.nan  # Sin hora — se asignará hora media del día
    except Exception:
        return None, np.nan


# ─────────────────────────────────────────
# PASO 1: CARGAR Y FILTRAR PRESENCIAS GBIF
# ─────────────────────────────────────────
def load_gbif_presences():
    print("\n[PASO 1] Cargando presencias GBIF...")
    df = pd.read_csv(GBIF_FILE, low_memory=False)
    print(f"  Total registros cargados: {len(df):,}")

    # Asegurar tipos numéricos
    df['decimalLatitude']  = pd.to_numeric(df['decimalLatitude'], errors='coerce')
    df['decimalLongitude'] = pd.to_numeric(df['decimalLongitude'], errors='coerce')
    df['year'] = pd.to_numeric(df['year'], errors='coerce')

    # Filtro geográfico: Bogotá Bounding Box
    df = df[
        (df['decimalLatitude'] >= BOGOTA_LAT_MIN) & (df['decimalLatitude'] <= BOGOTA_LAT_MAX) &
        (df['decimalLongitude'] >= BOGOTA_LON_MIN) & (df['decimalLongitude'] <= BOGOTA_LON_MAX)
    ].copy()
    
    # Filtro geográfico fino: Solo zona urbana (excluye cerros)
    df = df[is_strictly_urban(df['decimalLatitude'], df['decimalLongitude'])].copy()
    print(f"  Después de filtro geográfico (Bogotá Urbana Estricta): {len(df):,}")

    # Filtro temporal: solo años con datos de contaminación disponibles
    df = df[(df['year'] >= YEAR_MIN) & (df['year'] <= YEAR_MAX)].copy()
    print(f"  Después de filtro temporal ({YEAR_MIN}–{YEAR_MAX}): {len(df):,}")

    # Parsear eventDate
    parsed = df['eventDate'].apply(parse_gbif_eventdate)
    df['date']         = [p[0] for p in parsed]
    df['matched_hour'] = [p[1] for p in parsed]

    # Para registros sin hora, asignar hora media de observaciones (8am = hora pico)
    df['matched_hour'] = df['matched_hour'].fillna(8).astype(int)

    # Eliminar registros sin fecha válida
    df = df.dropna(subset=['date']).copy()
    print(f"  Después de parsear fechas: {len(df):,}")

    # Renombrar columnas para uniformidad
    df = df.rename(columns={
        'decimalLatitude': 'lat',
        'decimalLongitude': 'lon',
        'month': 'month'
    })

    df['month'] = pd.to_numeric(df['month'], errors='coerce').fillna(0).astype(int)

    return df[['lat', 'lon', 'date', 'matched_hour', 'month', 'year', 'gbifID', 'individualCount']].copy()


# ─────────────────────────────────────────
# PASO 2: SPATIAL THINNING
# ─────────────────────────────────────────
def apply_spatial_thinning(df, cell_size=THINNING_CELL_SIZE):
    """
    Retiene máximo 1 presencia por celda espacial de tamaño cell_size°.
    Reduce clustering y sesgo de observación en zonas populares.
    """
    print(f"\n[PASO 2] Aplicando spatial thinning (celda ~{cell_size*111:.0f}m)...")
    df = df.copy()
    df['grid_lat'] = (df['lat'] / cell_size).astype(int)
    df['grid_lon'] = (df['lon'] / cell_size).astype(int)

    # Conservar un registro por celda espacial POR CADA MES
    df_thinned = df.drop_duplicates(subset=['grid_lat', 'grid_lon', 'year', 'month'], keep='first')
    df_thinned = df_thinned.drop(columns=['grid_lat', 'grid_lon'])
    print(f"  Antes del thinning: {len(df):,} | Después (Espacio-Temporal): {len(df_thinned):,}")
    return df_thinned


# ─────────────────────────────────────────
# PASO 3: GENERAR PUNTOS DE FONDO (BACKGROUND)
# ─────────────────────────────────────────
def generate_background_points(df_presences, n_target=None, cell_size=BACKGROUND_CELL_SIZE):
    """
    Genera puntos de fondo (background/quadrature points) usando una grilla
    espacial regular sobre la bounding box de Bogotá.

    Metodología (Renner & Warton 2013 / Golini 2013):
    - Los puntos de fondo son puntos de CUADRATURA para aproximar la integral
      del proceso puntual de intensidad, NO son pseudo-ausencias biológicas.
    - Se usa grilla regular para garantizar cobertura uniforme del espacio ambiental.
    - Se asigna una fecha y hora aleatorias del rango de datos disponibles.
    - El peso de cuadratura = Área_total / N_puntos_fondo.
    """
    print(f"\n[PASO 3] Generando puntos de fondo (background/quadrature)...")

    # Crear grilla regular
    lat_vals = np.arange(BOGOTA_LAT_MIN, BOGOTA_LAT_MAX, cell_size)
    lon_vals = np.arange(BOGOTA_LON_MIN, BOGOTA_LON_MAX, cell_size)
    grid_lats, grid_lons = np.meshgrid(lat_vals, lon_vals)
    all_bg_lats = grid_lats.ravel()
    all_bg_lons = grid_lons.ravel()
    
    # Filtro geográfico fino: Solo zona urbana (excluye cerros)
    urban_mask = is_strictly_urban(all_bg_lats, all_bg_lons)
    all_bg_lats = all_bg_lats[urban_mask]
    all_bg_lons = all_bg_lons[urban_mask]
    
    total_grid = len(all_bg_lats)
    print(f"  Grilla generada: {total_grid:,} puntos urbanos")

    # Target de puntos de fondo
    if n_target is None:
        n_target = len(df_presences) * BACKGROUND_RATIO

    # Muestrear la grilla con reemplazo para alcanzar el n_target
    # Al tener reemplazo, el mismo punto geográfico puede aparecer varias veces
    # pero se le asignarán fechas distintas en el siguiente paso.
    idx = np.random.choice(total_grid, size=n_target, replace=True)
    bg_lats = all_bg_lats[idx]
    bg_lons = all_bg_lons[idx]

    # Asignar fechas y horas aleatorias del período analizado
    np.random.seed(42)
    # Generar fechas aleatorias entre 2022-01-01 y 2025-12-31
    start_date = pd.Timestamp('2022-01-01')
    end_date   = pd.Timestamp('2025-12-31')
    date_range_days = (end_date - start_date).days
    random_days = np.random.randint(0, date_range_days, size=len(bg_lats))
    random_dates = [str((start_date + pd.Timedelta(days=int(d))).date()) for d in random_days]
    random_hours = np.random.randint(6, 20, size=len(bg_lats))  # Horas diurnas (6am-8pm)
    random_months = [int(d[5:7]) for d in random_dates]
    random_years  = [int(d[:4]) for d in random_dates]

    # Calcular peso de cuadratura
    area_bogota_deg2 = (BOGOTA_LAT_MAX - BOGOTA_LAT_MIN) * (BOGOTA_LON_MAX - BOGOTA_LON_MIN)
    quadrature_weight = area_bogota_deg2 / len(bg_lats)

    df_bg = pd.DataFrame({
        'lat': bg_lats,
        'lon': bg_lons,
        'date': random_dates,
        'matched_hour': random_hours,
        'month': random_months,
        'year': random_years,
        'gbifID': np.nan,
        'individualCount': np.nan,
        'quadrature_weight': quadrature_weight,
        'source': 'background'
    })

    print(f"  Puntos de fondo generados: {len(df_bg):,}")
    print(f"  Peso de cuadratura por punto: {quadrature_weight:.6f} grados²")
    return df_bg


# ─────────────────────────────────────────
# PASO 4: PREPROCESAR CONTAMINACIÓN
# ─────────────────────────────────────────
def load_pollution():
    print(f"\n[PASO 4] Cargando y preprocesando datos de contaminación...")
    df_poll = pd.read_csv(POLLUTION_FILE, low_memory=False)
    print(f"  Registros de contaminación cargados: {len(df_poll):,}")

    # Normalizar unidades antes de pivotar. OpenAQ/RMCAB mezcla gases en ppm y
    # ug/m3; el modelo necesita una escala unica por contaminante.
    target_columns = {
        'co': 'co_ppm',
        'no2': 'no2_ppb',
        'o3': 'o3_ppb',
        'so2': 'so2_ppb',
        'pm10': 'pm10_ugm3',
        'pm25': 'pm25_ugm3',
    }
    molecular_weight = {
        'co': 28.01,
        'no2': 46.0055,
        'o3': 48.00,
        'so2': 64.066,
    }

    def normalize_unit(unit):
        unit = str(unit).strip().lower()
        unit = unit.replace('µ', 'u').replace('μ', 'u')
        # El CSV puede venir con mojibake: "ľg/mł" en vez de "ug/m3".
        unit = unit.replace('ľ', 'u').replace('ł', '3')
        unit = unit.replace('³', '3').replace('^3', '3')
        unit = unit.replace(' ', '')
        if unit in {'ug/m3', 'ugm3', 'ug/mł'}:
            return 'ug/m3'
        if unit in {'ppm', 'ppb'}:
            return unit
        return unit

    def convert_pollutant_value(row):
        parameter = str(row['parameter']).lower()
        value = row['value']
        unit = row['unit_norm']

        if pd.isna(value) or value < 0:
            return np.nan

        if parameter in {'pm10', 'pm25'}:
            return value if unit == 'ug/m3' else np.nan

        if parameter == 'co':
            if unit == 'ppm':
                return value
            if unit == 'ppb':
                return value / 1000.0
            if unit == 'ug/m3':
                return value * 24.45 / (molecular_weight[parameter] * 1000.0)

        if parameter in {'no2', 'o3', 'so2'}:
            if unit == 'ppb':
                return value
            if unit == 'ppm':
                return value * 1000.0
            if unit == 'ug/m3':
                return value * 24.45 / molecular_weight[parameter]

        return np.nan

    df_poll['parameter'] = df_poll['parameter'].astype(str).str.lower()
    df_poll['value'] = pd.to_numeric(df_poll['value'], errors='coerce')
    df_poll['unit_norm'] = df_poll['unit'].apply(normalize_unit)
    df_poll = df_poll[df_poll['parameter'].isin(target_columns)].copy()
    df_poll['value_converted'] = df_poll.apply(convert_pollutant_value, axis=1)
    df_poll['pollutant_column'] = df_poll['parameter'].map(target_columns)

    converted_summary = (
        df_poll
        .groupby(['parameter', 'unit_norm'])['value_converted']
        .agg(['count', 'median'])
        .reset_index()
    )
    print("  Unidades convertidas a: CO=ppm; NO2/O3/SO2=ppb; PM=ug/m3")
    print(converted_summary.to_string(index=False))

    # Convertir UTC a hora local de Bogotá (UTC-5)
    df_poll['datetime'] = pd.to_datetime(df_poll['datetime'], utc=True, errors='coerce')
    df_poll = df_poll.dropna(subset=['datetime'])
    df_poll['datetime_local'] = df_poll['datetime'] - pd.Timedelta(hours=5)
    df_poll['date'] = df_poll['datetime_local'].dt.date.astype(str)
    df_poll['hour'] = df_poll['datetime_local'].dt.hour

    # Pivotar: una fila por (estación, fecha, hora), columnas = contaminantes
    print("  Pivotando tabla de contaminación...")
    df_wide = df_poll.pivot_table(
        index=['station_name', 'date', 'hour'],
        columns='pollutant_column',
        values='value_converted',
        aggfunc='mean'
    ).reset_index()
    df_wide.columns.name = None

    print(f"  Tabla contaminación procesada: {len(df_wide):,} filas (estación × fecha × hora)")
    return df_wide


# ─────────────────────────────────────────
# PASO 5 & 6: MERGE Y ENSAMBLE FINAL
# ─────────────────────────────────────────
def merge_with_pollution(df_points, df_poll_wide, df_stations, label="puntos"):
    """
    Une df_points con contaminacion usando estacion mas cercana + fecha.
    Usa el promedio diario de contaminacion por estacion+fecha para maximizar
    el numero de matches (la hora exacta solo cubre ~5% de los registros GBIF).
    """
    # Asignar estacion mas cercana
    df_points = assign_nearest_station(df_points, df_stations)

    # Filtrar puntos demasiado lejos
    before = len(df_points)
    df_points = df_points[df_points['distance_km'] <= MAX_DISTANCE_KM].copy()
    print(f"  [{label}] Descartados {before - len(df_points):,} puntos a > {MAX_DISTANCE_KM}km de estacion.")

    pollutant_cols_all = ['co_ppm', 'no2_ppb', 'o3_ppb', 'pm10_ugm3', 'pm25_ugm3', 'so2_ppb']
    existing_pollutants = [c for c in pollutant_cols_all if c in df_poll_wide.columns]

    # Calcular promedio diario: agrupa por estacion y fecha
    df_daily = (
        df_poll_wide
        .groupby(['station_name', 'date'])[existing_pollutants]
        .mean()
        .reset_index()
    )

    # Merge: cada punto busca su estacion mas cercana + su fecha
    df_merged = df_points.merge(
        df_daily,
        left_on=['nearest_station', 'date'],
        right_on=['station_name', 'date'],
        how='left'
    ).drop(columns=['station_name'], errors='ignore')

    # Mantener solo registros con al menos un contaminante medido
    df_merged = df_merged.dropna(subset=existing_pollutants, how='all')
    print(f"  [{label}] Con al menos 1 contaminante medido: {len(df_merged):,}")
    return df_merged


def run():
    np.random.seed(42)
    print("=" * 60)
    print("  BUILD PRESENCE-ONLY DATASET — Modelo Golini")
    print("=" * 60)

    # Cargar datos auxiliares
    df_stations = pd.read_csv(STATIONS_FILE)

    # Paso 1: Presencias GBIF
    df_pres = load_gbif_presences()

    # Paso 2: Spatial thinning
    df_pres = apply_spatial_thinning(df_pres)
    n_presences = len(df_pres)

    # Paso 3: Puntos de fondo
    df_bg = generate_background_points(df_pres, n_target=n_presences * BACKGROUND_RATIO)

    # Agregar columnas de trazabilidad a presencias
    df_pres['quadrature_weight'] = 0.0  # Las presencias tienen peso 0 (son "casos")
    df_pres['source'] = 'gbif'

    # Paso 4: Contaminación
    df_poll = load_pollution()

    # Paso 5: Merge presencias + contaminación
    print("\n[PASO 5] Uniendo PRESENCIAS con contaminación...")
    df_pres_merged = merge_with_pollution(df_pres, df_poll, df_stations, label="presencias")
    df_pres_merged['y'] = 1

    # Paso 5b: Merge fondo + contaminación
    print("\n[PASO 5b] Uniendo FONDO (background) con contaminación...")
    df_bg_merged = merge_with_pollution(df_bg, df_poll, df_stations, label="fondo")
    df_bg_merged['y'] = 0

    # Paso 6: Ensamble final
    print("\n[PASO 6] Ensamblando dataset final...")
    df_final = pd.concat([df_pres_merged, df_bg_merged], ignore_index=True)

    # Ordenar columnas
    id_cols = ['y', 'source', 'lat', 'lon', 'date', 'matched_hour', 'month', 'year',
               'nearest_station', 'distance_km', 'quadrature_weight']
    pollutant_cols = ['co_ppm', 'no2_ppb', 'o3_ppb', 'pm10_ugm3', 'pm25_ugm3', 'so2_ppb']
    extra_cols = [c for c in df_final.columns if c not in id_cols + pollutant_cols]

    final_cols = id_cols + [c for c in pollutant_cols if c in df_final.columns] + extra_cols
    df_final = df_final[[c for c in final_cols if c in df_final.columns]]

    # Guardar
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False)

    # Resumen final
    n_pres_final  = (df_final['y'] == 1).sum()
    n_bg_final    = (df_final['y'] == 0).sum()
    print("\n" + "=" * 60)
    print(f"  [OK] Dataset guardado: {OUTPUT_FILE}")
    print(f"  ---------------------------------")
    print(f"  Presencias (y=1): {n_pres_final:,}")
    print(f"  Fondo     (y=0): {n_bg_final:,}")
    print(f"  Total          : {len(df_final):,}")
    print(f"  Columnas       : {list(df_final.columns)}")

    poll_miss = df_final[[c for c in pollutant_cols if c in df_final.columns]].isna().mean()
    print(f"\n  Tasa de NaN por contaminante:")
    for col, rate in poll_miss.items():
        print(f"    {col}: {rate*100:.1f}% NaN")
    print("=" * 60)


if __name__ == "__main__":
    run()
