# EDA - Modelo de Presencia-Only (Golini)

Este reporte analiza el dataset final de **3457 registros**, compuesto por:
- **1480 Presencias (y=1)** provenientes de GBIF.
- **1977 Puntos de Fondo (y=0)** generados por grilla espacial.

## 1. Análisis de Cobertura (Valores Nulos)

| Contaminante | % Nulos |
|:---|:---|
| co_ppm | 60.7% |
| no2_ppb | 7.5% |
| o3_ppb | 26.6% |
| pm10_ugm3 | 53.1% |
| pm25_ugm3 | 75.5% |
| so2_ppb | 57.8% |

## 2. Estadísticas Descriptivas por Grupo
| level_0   | level_1   |         0 |         1 |
|:----------|:----------|----------:|----------:|
| co_ppm    | median    |  0.416622 |  0.502933 |
| co_ppm    | std       |  0.304511 |  0.324008 |
| no2_ppb   | median    |  6.0565   |  7.74554  |
| no2_ppb   | std       | 10.7108   | 17.062    |
| o3_ppb    | median    | 27.7246   | 17.9638   |
| o3_ppb    | std       | 14.2561   | 14.2568   |
| pm10_ugm3 | median    | 19.9114   | 21.1958   |
| pm10_ugm3 | std       | 14.7748   | 14.0768   |
| pm25_ugm3 | median    | 19.2173   | 15.2778   |
| pm25_ugm3 | std       |  7.74332  |  7.9673   |
| so2_ppb   | median    |  0.47822  |  1.11643  |
| so2_ppb   | std       |  1.49908  |  3.37177  |

## 3. Visualización de Distribuciones
![Distribuciones](plots/pollutant_distributions_presence_only.png)

## 4. Mapa Interactivo
Se ha generado un mapa interactivo con Folium en: [presence_only_map.html](plots/presence_only_map.html)