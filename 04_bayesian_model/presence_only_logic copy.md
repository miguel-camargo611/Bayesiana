# Lógica del Modelo Bayesiano de Presencia-Only (Golini)

Esta guía detalla el fundamento matemático y el algoritmo de estimación del modelo de **Presencia-Only Bayesiano** que aplicaremos al estudio del Copetón en Bogotá, siguiendo la metodología de la tesis doctoral de Natalia Golini (2013).

---

## 1. El Problema Fundamental: Datos Presence-Only

### 1.1 El Dato Oportunista (GBIF)
Los datos de GBIF representan registros donde *alguien* vio un Copetón. Formalmente, si $y_i = 1$, sabemos con certeza que el ave estaba ahí y el observador la reportó. 
Sin embargo, no tenemos verdaderas ausencias ($y_i = 0$ biológicas garantizadas), ya que la falta de un registro en GBIF puede significar que el ave no estaba, o simplemente que ningún observador pasó por ahí.

### 1.2 El Enfoque Presence-Background
Para inferir los requerimientos de hábitat sin verdaderas ausencias, utilizamos un diseño **Presence-Background** (a menudo comparado con un diseño de *Caso-Control* en epidemiología):

| Tipo de Punto | Definición | Variable $y$ |
|:---|:---|:---|
| **Presencia (Caso)** | Registro confirmado en GBIF | $y_i = 1$ |
| **Fondo (Control)** | Puntos muestreados del espacio disponible | $y_i = 0$ |

**Concepto Clave**: Los puntos de fondo ($y=0$) **no son verdaderas ausencias biológicas**. Simplemente representan las condiciones ambientales (contaminación) que están *disponibles* en Bogotá. Al comparar las condiciones donde el ave fue vista ($y=1$) contra lo que estaba disponible en el fondo ($y=0$), el modelo aprende qué condiciones resultan en un mayor **Relative Environmental Suitability** (Idoneidad Ambiental Relativa) para la especie.

### 1.3 Sampling Bias (Sesgo de Muestreo)
Es crucial reconocer que las observaciones de GBIF son oportunistas y están espacialmente sesgadas hacia áreas urbanas accesibles, parques (como el Jardín Botánico) y regiones con mayor actividad de observadores. Para mitigar este efecto y evitar que el modelo aprenda la distribución de los pajareros en lugar de la distribución del ave, hemos aplicado **Spatial-Temporal Thinning** (raleo espacio-temporal) al dataset, asegurando una muestra mucho más representativa de las condiciones ambientales subyacentes.

---

## 2. El Modelo: Bayesian Logistic Regression

En la ecología moderna, este problema se modela de manera elegante y directa utilizando una **Regresión Logística Bayesiana**. 

### 2.1 La Distribución de la Respuesta (Likelihood)
Asumimos que la clasificación de un punto como presencia ($y=1$) o fondo ($y=0$) sigue una distribución Bernoulli guiada por una intensidad relativa $\psi_i$:

$$y_i \sim \text{Bernoulli}(\psi_i)$$

donde $\psi_i$ se modela a través de una función de enlace logit:

$$\psi_i = \frac{e^{\eta_i}}{1 + e^{\eta_i}}$$

### 2.2 El Predictor Lineal ($\eta_i$)
El predictor lineal conecta las variables ambientales con la intensidad relativa de presencia:

$$\eta_i = \beta_0 + \beta_{PM10} \cdot PM10_i^* + \beta_{O3} \cdot O3_i^* + \beta_{NO2} \cdot NO2_i^* + \beta_{CO} \cdot CO_i^* + \beta_{SO2} \cdot SO2_i^*$$

*(Nota: El superíndice $*$ indica que las covariables han sido **estandarizadas** (media 0, desviación estándar 1). Esto es crítico en modelos Bayesianos para asegurar la convergencia del algoritmo MCMC y hacer los efectos comparables).*

### 2.3 Multicolinealidad (Multicollinearity)
Dado que los contaminantes urbanos suelen estar correlacionados (e.g., el tráfico emite tanto $NO_2$ como $CO$), es fundamental examinar la multicolinealidad antes del ajuste final. Utilizaremos matrices de correlación y posiblemente el cálculo del *Variance Inflation Factor (VIF)* en la fase exploratoria para asegurar que los parámetros $\beta$ mantengan su identificabilidad y significado ecológico individual.

---

## 3. Las Distribuciones A Priori (Priors)

Siguiendo la filosofía Bayesiana estándar para modelos de regresión donde no tenemos conocimiento previo hiper-específico, asignamos **priors débilmente informativos** (o de regularización) a nuestros coeficientes:

$$\beta_k \sim \mathcal{N}(0, 1) \quad \forall k$$

Una varianza de 1 en la escala *log-odds* es lo suficientemente flexible para permitir efectos desde nulos hasta muy fuertes, pero restringe matemáticamente al algoritmo para que no explore valores absurdos (e.g., odds ratios de miles de millones).

**El Intercepto ($\beta_0$)**: En la regresión logística Presence-Background, el intercepto generalmente **no tiene una interpretación ecológica directa**, ya que absorbe la fracción de muestreo desconocida (sampling fraction) y la prevalencia implícita de la especie. Por ende, usamos un prior ligeramente más difuso o centrado en la proporción de los datos, pero no derivaremos conclusiones biológicas de su valor posterior.

---

## 4. Contexto Teórico Adicional (Opcional)

Existen extensiones más complejas en la literatura para abordar este problema, aunque introducen considerables desafíos de identificabilidad:

1.  **Latent Occupancy Augmentation**: Metodologías clásicas (como algunas propuestas por Golini) intentan imputar el verdadero estado biológico de los puntos de fondo usando variables latentes discretas ($Z_j \sim \text{Bernoulli}$). Aunque teóricamente riguroso, mezclar la imputación de falsos negativos con el diseño de background suele causar redundancia y problemas de convergencia en MCMC modernos.
2.  **Inhomogeneous Poisson Process (IPP)**: Renner & Warton (2013) demostraron que la regresión logística sobre puntos de fondo aproxima un IPP si se utilizan *pesos de cuadratura* proporcionales al área.
3.  **Pólya-Gamma**: Usada para acelerar muestreadores de Gibbs linearizando el logit.

**Para nuestra implementación en PyMC**, mantendremos el modelo en su forma más pura y estándar (Regresión Logística), delegando toda la complejidad computacional al algoritmo **NUTS (No-U-Turn Sampler)**, el cual maneja la geometría logística de manera impecable sin necesidad de pesos IPP o imputación de variables latentes.

---

## 5. Implementación del Modelo en PyMC

Con nuestra formulación sólida y simplificada, el código en PyMC es directo, transparente y computacionalmente eficiente:

```python
import pymc as pm
import numpy as np

# X_std: matriz de covariables estandarizadas (presencias + fondo)
# y_obs: vector de observaciones (1 para GBIF, 0 para fondo)

with pm.Model() as bayesian_pb_model:

    # 1. Priors para los coeficientes (Efectos de la contaminación)
    beta = pm.Normal("beta", mu=0, sigma=1, shape=X_std.shape[1])
    
    # Prior para el intercepto (intensidad base / bias de muestreo)
    beta_0 = pm.Normal("beta_0", mu=0, sigma=2)

    # 2. Predictor Lineal (Logit)
    eta = beta_0 + pm.math.dot(X_std, beta)
    
    # 3. Función de Enlace (Inversa Logit)
    psi = pm.math.invlogit(eta)

    # 4. Likelihood (Distribución de los Datos Observados)
    obs = pm.Bernoulli("obs", p=psi, observed=y_obs)

    # 5. Muestreo NUTS
    trace = pm.sample(draws=2000, tune=1000, target_accept=0.9, return_inferencedata=True)
```

---

## 6. Interpretación de la Inferencia Posterior

Al concluir el MCMC, obtendremos distribuciones posteriores completas para cada coeficiente $\beta_k$:

| Medida Posterior | Interpretación Ecológica |
|:---|:---|
| **Mediana Posterior** | El efecto estimado más probable del contaminante. |
| **Intervalo HDI 95%** | El Rango de Credibilidad. Tenemos un 95% de certeza Bayesiana de que el verdadero efecto cae aquí. |
| **$\beta_k < 0$ (Certeza alta)** | El contaminante afecta negativamente la presencia del Copetón. |
| **$OR_k = e^{\beta_k}$** | **Odds Ratio**: Por cada aumento de 1 Desviación Estándar en la contaminación, el *Relative Environmental Suitability* (Idoneidad Ambiental Relativa) se multiplica por $OR$. |
