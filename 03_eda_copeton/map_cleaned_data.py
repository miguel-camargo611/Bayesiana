import pandas as pd
import folium
import os

# Configuración de rutas
BASE_DIR = os.getcwd()
DATA_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'copeton_presence_only_ready.csv')
STATIONS_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'bogota_stations_coords.csv')
OUTPUT_PATH = os.path.join(BASE_DIR, 'presence_only_map.html')

def create_map():
    print("Cargando datos...")
    if not os.path.exists(DATA_PATH):
        print(f"Error: No se encuentra {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)
    
    # Filtrar para los 1,355 registros (PM10, NO2, O3)
    df_clean = df.dropna(subset=['pm10_ugm3', 'no2_ppb', 'o3_ppb']).copy()
    
    # Crear el mapa base centrado en Bogotá
    # Usamos CartoDB Positron para un look limpio y profesional
    m = folium.Map(location=[4.65, -74.10], zoom_start=11, tiles='cartodbpositron')
    
    # Agregar estaciones de monitoreo para contexto
    if os.path.exists(STATIONS_PATH):
        df_stations = pd.read_csv(STATIONS_PATH)
        # Filtrar estaciones con coordenadas válidas de Bogotá
        df_stations = df_stations[(df_stations['lat'] >= 4.4) & (df_stations['lat'] <= 4.9)]
        
        for _, st in df_stations.iterrows():
            folium.Marker(
                location=[st['lat'], st['lon']],
                popup=f"Estación: {st['station_name']}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)

    # Capas para Presencias y Fondo
    fg_pres = folium.FeatureGroup(name='Presencias (Copetones)')
    fg_bg = folium.FeatureGroup(name='Fondo (Background/Puntos de Control)')

    print(f"Procesando {len(df_clean)} registros...")
    
    for _, row in df_clean.iterrows():
        # Estética Premium:
        # Presencia -> Esmeralda vibrante
        # Fondo -> Gris azulado profundo
        if row['y'] == 1:
            color = '#10b981'
            target_group = fg_pres
        else:
            color = '#4b5563'
            target_group = fg_bg
            
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=3.5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1,
            popup=(f"<b>Tipo:</b> {'Presencia' if row['y']==1 else 'Fondo'}<br>"
                   f"<b>Estación Cercana:</b> {row['nearest_station']}<br>"
                   f"<b>PM10:</b> {row['pm10_ugm3']:.1f} µg/m³<br>"
                   f"<b>NO2:</b> {row['no2_ppb']:.1f} ppb<br>"
                   f"<b>O3:</b> {row['o3_ppb']:.1f} ppb")
        ).add_to(target_group)

    fg_bg.add_to(m)
    fg_pres.add_to(m)
    
    # Control de capas
    folium.LayerControl().add_to(m)
    
    # Guardar
    m.save(OUTPUT_PATH)
    print(f"¡Mapa generado con éxito en: {OUTPUT_PATH}")

if __name__ == "__main__":
    create_map()
