import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'copeton_occupancy_ready.csv')
EDA_DIR = os.path.join(BASE_DIR, 'eda_copeton')
PLOT_DIR = os.path.join(EDA_DIR, 'plots')

os.makedirs(PLOT_DIR, exist_ok=True)

def analyze():
    print(f"Reading dataset: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE)
    
    # 1. General Info
    print("\n--- INFO GENERAL ---")
    print(df.info())
    
    # 2. Nulls & Duplicates
    print("\n--- NULOS Y DUPLICADOS ---")
    print("Nulos por columna:\n", df.isnull().sum())
    print("Duplicados totales:", df.duplicated().sum())
    
    # 3. Class Balance (y_copeton)
    print("\n--- BALANCE DE CLASES (y) ---")
    counts = df['y_copeton'].value_counts(normalize=True) * 100
    print(f"Detectado (1): {counts.get(1, 0):.2f}%")
    print(f"No Detectado (0): {counts.get(0, 0):.2f}%")
    
    plt.figure(figsize=(6, 4))
    sns.countplot(x='y_copeton', data=df, palette='viridis')
    plt.title('Distribución de Detecciones (y_copeton)')
    plt.savefig(os.path.join(PLOT_DIR, 'class_balance.png'))
    plt.close()
    
    # 4. Outliers & Distributions
    print("\n--- ESTADÍSTICOS Y OUTLIERS ---")
    num_cols = [
        'pm10_ugm3', 'pm25_ugm3', 'so2_ugm3', 'co_ppm', 'no2_ppb', 'o3_ppb',
        'DURATION MINUTES', 'EFFORT DISTANCE KM', 'NUMBER OBSERVERS'
    ]
    
    desc = df[num_cols].describe()
    print(desc)
    
    # Detect outliers with IQR
    for col in num_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df[(df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))]
        print(f"Outliers en {col}: {len(outliers)} ({len(outliers)/len(df)*100:.2f}%)")

    # Plot Distributions
    plt.figure(figsize=(15, 12))
    for i, col in enumerate(num_cols):
        plt.subplot(3, 3, i+1)
        sns.histplot(df[col], kde=True)
        plt.title(f'Distribución: {col}')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, 'distributions.png'))
    plt.close()

    # 5. Correlations
    print("\n--- CORRELACIONES ---")
    plt.figure(figsize=(12, 10))
    corr = df[num_cols + ['y_copeton']].corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", mask=mask)
    plt.title('Matriz de Correlación')
    plt.savefig(os.path.join(PLOT_DIR, 'correlation_matrix.png'))
    plt.close()

    # 6. Analysis by Site (Station)
    print("\n--- ANÁLISIS POR ESTACIÓN ---")
    station_stats = df.groupby('nearest_station')['y_copeton'].agg(['count', 'sum', 'mean'])
    station_stats.columns = ['Total Visitas', 'Detecciones', 'Frecuencia Relativa']
    print(station_stats)
    
    plt.figure(figsize=(12, 6))
    sns.barplot(x=station_stats.index, y=station_stats['Frecuencia Relativa'])
    plt.title('Frecuencia de Detección por Estación')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, 'station_detections.png'))
    plt.close()

    print(f"\nEDA completado. Resultados en {EDA_DIR}")

if __name__ == "__main__":
    analyze()
