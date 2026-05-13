import pandas as pd
import numpy as np
import os
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import folium
from folium.plugins import MarkerCluster

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'copeton_presence_only_ready.csv')
PLOT_DIR = os.path.join(BASE_DIR, '03_eda_copeton', 'plots')
os.makedirs(PLOT_DIR, exist_ok=True)
REPORT_FILE = os.path.join(BASE_DIR, '03_eda_copeton', 'presence_only_eda_report.md')
MAP_FILE = os.path.join(PLOT_DIR, 'presence_only_map.html')

def perform_eda():
    print(f"Cargando datos de: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE)
    
    # Basic Stats
    n_total = len(df)
    n_pres = (df['y'] == 1).sum()
    n_bg = (df['y'] == 0).sum()
    
    pollutant_cols = ['co_ppm', 'no2_ppb', 'o3_ppb', 'pm10_ugm3', 'pm25_ugm3', 'so2_ppb']
    
    # 1. Report Header
    report = []
    report.append("# EDA - Modelo de Presencia-Only (Golini)")
    report.append(f"\nEste reporte analiza el dataset final de **{n_total} registros**, compuesto por:")
    report.append(f"- **{n_pres} Presencias (y=1)** provenientes de GBIF.")
    report.append(f"- **{n_bg} Puntos de Fondo (y=0)** generados por grilla espacial.")
    
    # 2. Null Analysis
    report.append("\n## 1. Análisis de Cobertura (Valores Nulos)")
    report.append("\n| Contaminante | % Nulos |")
    report.append("|:---|:---|")
    for col in pollutant_cols:
        null_pct = df[col].isna().mean() * 100
        report.append(f"| {col} | {null_pct:.1f}% |")
    
    # 3. Descriptive Stats
    report.append("\n## 2. Estadísticas Descriptivas por Grupo")
    stats_df = df.groupby('y')[pollutant_cols].agg(['median', 'std']).T.reset_index()
    report.append(stats_df.to_markdown(index=False))
    
    # 4. Plots
    print("Generando gráficos...")
    # Distribution plots
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    for i, col in enumerate(pollutant_cols):
        sns.kdeplot(data=df[df['y']==1], x=col, label='Presencia (GBIF)', ax=axes[i], fill=True, color='green')
        sns.kdeplot(data=df[df['y']==0], x=col, label='Fondo (Background)', ax=axes[i], fill=True, color='blue')
        axes[i].set_title(f'Distribución de {col}')
        axes[i].legend()
    
    plt.tight_layout()
    dist_plot_path = os.path.join(PLOT_DIR, 'pollutant_distributions_presence_only.png')
    plt.savefig(dist_plot_path)
    plt.close()
    
    report.append("\n## 3. Visualización de Distribuciones")
    report.append(f"![Distribuciones](plots/pollutant_distributions_presence_only.png)")
    
    # 5. Folium Map
    print("Generando mapa de Folium...")
    # Center of Bogota
    m = folium.Map(location=[4.65, -74.1], zoom_start=11, tiles='cartodbpositron')
    
    # Presence Cluster
    pres_cluster = MarkerCluster(name='Presencias GBIF').add_to(m)
    for idx, row in df[df['y']==1].iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=4,
            color='green',
            fill=True,
            fill_color='green',
            popup=f"Presencia GBIF\nFecha: {row['date']}",
            tooltip="GBIF Presence"
        ).add_to(pres_cluster)
        
    # Background Cluster
    bg_cluster = MarkerCluster(name='Puntos de Fondo').add_to(m)
    for idx, row in df[df['y']==0].iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=3,
            color='blue',
            fill=True,
            fill_color='blue',
            popup=f"Punto de Fondo\nCuadratura: {row['quadrature_weight']:.6f}",
            tooltip="Background Point"
        ).add_to(bg_cluster)
    
    folium.LayerControl().add_to(m)
    m.save(MAP_FILE)
    
    report.append("\n## 4. Mapa Interactivo")
    report.append(f"Se ha generado un mapa interactivo con Folium en: [presence_only_map.html](plots/presence_only_map.html)")
    
    # 6. Save Report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    
    print(f"\nEDA completado exitosamente.")
    print(f"- Reporte: {REPORT_FILE}")
    print(f"- Mapa: {MAP_FILE}")

if __name__ == "__main__":
    perform_eda()
