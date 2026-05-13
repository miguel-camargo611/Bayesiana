import os

import folium
import pandas as pd


BASE_DIR = os.getcwd()
DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "copeton_presence_only_model_ready_pm10_no2_o3.csv",
)
STATIONS_PATH = os.path.join(BASE_DIR, "data", "raw", "bogota_stations_coords.csv")
ROOT_OUTPUT_PATH = os.path.join(BASE_DIR, "presence_only_map_pm10_no2_o3.html")
PLOTS_OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "03_eda_copeton",
    "plots",
    "presence_only_map_pm10_no2_o3.html",
)


def add_station_layer(map_obj):
    if not os.path.exists(STATIONS_PATH):
        return

    df_stations = pd.read_csv(STATIONS_PATH)
    df_stations = df_stations[
        (df_stations["lat"] >= 4.4)
        & (df_stations["lat"] <= 4.9)
        & (df_stations["lon"] >= -74.3)
        & (df_stations["lon"] <= -73.9)
    ]

    station_group = folium.FeatureGroup(
        name="Estaciones RMCAB",
        show=True,
    )

    for _, station in df_stations.iterrows():
        folium.Marker(
            location=[station["lat"], station["lon"]],
            popup=f"Estacion: {station['station_name']}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(station_group)

    station_group.add_to(map_obj)


def create_map():
    print("Cargando dataset model-ready PM10 + NO2 + O3...")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"No se encuentra {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    df_clean = df.dropna(subset=["lat", "lon", "pm10_ugm3", "no2_ppb", "o3_ppb"]).copy()

    map_obj = folium.Map(
        location=[4.65, -74.10],
        zoom_start=11,
        tiles="cartodbpositron",
    )

    add_station_layer(map_obj)

    presence_group = folium.FeatureGroup(name="Presencias (Copetones)")
    background_group = folium.FeatureGroup(name="Fondo (Background)")

    print(f"Procesando {len(df_clean)} registros...")
    for _, row in df_clean.iterrows():
        is_presence = int(row["y"]) == 1
        color = "#10b981" if is_presence else "#4b5563"
        target_group = presence_group if is_presence else background_group
        kind = "Presencia" if is_presence else "Fondo"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=3.5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1,
            popup=(
                f"<b>Tipo:</b> {kind}<br>"
                f"<b>Fecha:</b> {row['date']}<br>"
                f"<b>Hora:</b> {int(row['matched_hour'])}<br>"
                f"<b>Estacion cercana:</b> {row['nearest_station']}<br>"
                f"<b>Distancia:</b> {row['distance_km']:.2f} km<br>"
                f"<b>PM10:</b> {row['pm10_ugm3']:.1f} ug/m3<br>"
                f"<b>NO2:</b> {row['no2_ppb']:.1f} ppb<br>"
                f"<b>O3:</b> {row['o3_ppb']:.1f} ppb"
            ),
        ).add_to(target_group)

    background_group.add_to(map_obj)
    presence_group.add_to(map_obj)
    folium.LayerControl(collapsed=False).add_to(map_obj)

    os.makedirs(os.path.dirname(PLOTS_OUTPUT_PATH), exist_ok=True)
    map_obj.save(ROOT_OUTPUT_PATH)
    map_obj.save(PLOTS_OUTPUT_PATH)
    print(f"Mapa generado en: {ROOT_OUTPUT_PATH}")
    print(f"Copia generada en: {PLOTS_OUTPUT_PATH}")


if __name__ == "__main__":
    create_map()
