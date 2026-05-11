"""
explore_cerros_and_hourly.py
Analiza la distribucion espacial de avistamientos (cerros vs interior)
y el potencial de usar promedios horarios para aumentar registros.
"""
import pandas as pd
import numpy as np
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Cargar GBIF ────────────────────────────────────────────────────
gbif = pd.read_csv('NUEVO/copeton_gbif.csv', low_memory=False)
gbif['decimalLatitude']  = pd.to_numeric(gbif['decimalLatitude'],  errors='coerce')
gbif['decimalLongitude'] = pd.to_numeric(gbif['decimalLongitude'], errors='coerce')
gbif['year']             = pd.to_numeric(gbif['year'],             errors='coerce')

urban = gbif[
    (gbif['decimalLatitude']  >= 4.55) & (gbif['decimalLatitude']  <= 4.77) &
    (gbif['decimalLongitude'] >= -74.18) & (gbif['decimalLongitude'] <= -74.01) &
    (gbif['year'] >= 2021) & (gbif['year'] <= 2026)
].copy()
print(f"Total zona urbana 2021-2026: {len(urban):,}")

# ── 1. Análisis de cerros: todos los registros al este de lon = -74.055 ──────
# Los cerros orientales de Bogota estan estrictamente al este
# El borde urbano-cerro se puede estimar alrededor de -74.055
# (Av de los Cerros / Via Circunvalar)
LON_CERROS = -74.055  

cerros = urban[urban['decimalLongitude'] > LON_CERROS]
interior = urban[urban['decimalLongitude'] <= LON_CERROS]

print(f"\nAl ESTE  de lon={LON_CERROS} (zona cerros): {len(cerros):,}")
print(f"Al OESTE de lon={LON_CERROS} (zona interior): {len(interior):,}")

print("\nDistribucion lon bins en zona de cerros:")
bins = [-74.055, -74.04, -74.03, -74.02, -74.01]
cerros['lon_bin'] = pd.cut(cerros['decimalLongitude'], bins=bins)
print(cerros.groupby('lon_bin', observed=True).size().to_string())

# Mostrar locaciones clave de cerros
cerros_kw = ['cerro','paramo','parque ecol','mont','verj','monser','guadalu','sorat','verjón','verjón']
cerros['is_cerro'] = cerros['locality'].str.lower().str.contains('|'.join(cerros_kw), na=False)
print(f"\nLocalities con keywords 'cerro': {cerros['is_cerro'].sum():,}")
unique_cerro = cerros[cerros['is_cerro']][['locality','decimalLatitude','decimalLongitude']].drop_duplicates()
for _, r in unique_cerro.iterrows():
    loc = str(r['locality'])[:70]
    print(f"  [{r['decimalLatitude']:.4f}, {r['decimalLongitude']:.4f}] {loc}")

# ── 2. Análisis de promedios horarios ─────────────────────────────
print("\n" + "="*60)
print("ANALISIS DE PROMEDIOS HORARIOS")
print("="*60)

poll = pd.read_csv('data/raw/bogota_pollution_hourly.csv', low_memory=False)
poll['datetime'] = pd.to_datetime(poll['datetime'], utc=True, errors='coerce')
poll = poll.dropna(subset=['datetime'])
poll['datetime_local'] = poll['datetime'] - pd.Timedelta(hours=5)
poll['date'] = poll['datetime_local'].dt.date.astype(str)
poll['hour'] = poll['datetime_local'].dt.hour
poll['year'] = poll['datetime_local'].dt.year

# Pivot wide (estacion x fecha x hora)
rename_map = {'co':'co_ppm','no2':'no2_ppb','o3':'o3_ppb',
              'pm10':'pm10_ugm3','pm25':'pm25_ugm3','so2':'so2_ugm3'}
poll['parameter'] = poll['parameter'].map(rename_map).fillna(poll['parameter'])
df_wide = poll.pivot_table(index=['station_name','date','hour'], columns='parameter',
                           values='value', aggfunc='mean').reset_index()
df_wide.columns.name = None
pollcols = ['co_ppm','no2_ppb','o3_ppb','pm10_ugm3','pm25_ugm3','so2_ugm3']
existing = [c for c in pollcols if c in df_wide.columns]

# Fechas con datos de contaminacion (>= 2021)
df_recent = df_wide[df_wide['date'] >= '2021-01-01']
poll_dates = set(df_recent['date'].unique())

# Registros GBIF interior matcheables por fecha
def parse_date(d):
    if pd.isna(d): return None
    return str(d)[:10] if len(str(d)) >= 10 else None

interior['date'] = interior['eventDate'].apply(parse_date)
n_matcheable = interior[interior['date'].isin(poll_dates)].shape[0]
print(f"Interior matcheable por fecha: {n_matcheable:,} de {len(interior):,}")

# Disponibilidad horaria de las estaciones por hora del dia
print("\nCobertura horaria de las estaciones (cuantos dias tienen medicion por hora):")
cov_h = df_recent.groupby('hour')[existing].count()
print(cov_h.to_string())
