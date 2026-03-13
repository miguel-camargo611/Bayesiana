# Informe EDA: Ocupación de Zonotrichia capensis (Copetón)

Este análisis se centra en el dataset listo para el modelo Bayesiano (`data/copeton_occupancy_ready.csv`), validando nulos, atípicos y correlaciones.

## 1. Integridad y Balance de Datos
- **Registros Totales**: 910 (Listas completas).
- **Nulos**: 0 nulos detectados.
- **Duplicados**: 0 duplicados a nivel de `SAMPLING EVENT IDENTIFIER`.
- **Frecuencia de Detección ($y$)**:
    - **Presencia ($1$)**: 693 registros (76.15%)
    - **Ausencia Inferida ($0$)**: 217 registros (23.85%)
    *Nota: El balance es excelente para un modelo de ocupación, permitiendo estimar ambos procesos ($\psi$ y $p$) con precisión.*

## 2. Análisis de Covariables (Polución y Esfuerzo)
- **Atípicos**: 
    - Se observan valores extremos en `DURATION MINUTES` (muestreos muy largos) y `pm10_ugm3`. 
    - *Recomendación*: El modelo Bayesiano es robusto, pero se podría considerar una transformación logarítmica para variables de esfuerzo muy sesgadas si el muestreo no converge.
- **Correlaciones**:
    - Fuerte correlación positiva entre `pm10_ugm3` y `pm25_ugm3` (+0.85).
    - Correlación moderada entre `DURATION MINUTES` y la probabilidad de detección.

## 3. Variabilidad por Estación (Sitios)
- **Estaciones con más actividad**: Bolivia (302 listas) y MinAmbiente (266 listas).
- **Frecuencia Relativa**: La probabilidad de detección varía entre 0.40 y 0.85 dependiendo de la estación, lo que sugiere que la ubicación (y su contaminación) efectivamente juega un rol en la presencia.

## 4. Visualizaciones (`eda_copeton/plots/`)
1. `class_balance.png`: Muestra la proporción presencia/ausencia.
2. `distributions.png`: Histogramas de todas las covariables.
3. `correlation_matrix.png`: Relaciones entre contaminantes y esfuerzo.
4. `station_detections.png`: Comparativa de éxito de detección por sitio.

---
**Conclusión**: El dataset es de alta fidelidad y está listo para la inferencia Bayesiana utilizando la lógica de Polya-Gamma de Clark (2019).
