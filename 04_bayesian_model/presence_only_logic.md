# Lógica del Modelo Bayesiano de Presencia-Only

Esta guía detalla el fundamento matemático y el algoritmo de estimación del modelo de Presencia-Only Bayesiano aplicado al estudio del Copetón en Bogotá. El enfoque sigue la literatura moderna de modelos Presence-Background, integrando ideas de la tesis doctoral de Natalia Golini (2013) y trabajos teóricos como Ward et al. (2009), Fithian & Hastie (2013) y Renner & Warton (2013).

---

# 1. El Problema Fundamental: Datos Presence-Only

## 1.1 El Dato Oportunista (GBIF)

Los datos de GBIF representan registros donde un observador detectó un Copetón. Formalmente, si:

$$
y_i = 1
$$

sabemos que el ave estuvo presente y fue reportada.

Sin embargo, no disponemos de verdaderas ausencias biológicas:

$$
y_i = 0
$$

La ausencia de un registro puede significar:

- que el ave realmente no estaba presente,
- o que simplemente no hubo observadores en esa ubicación.

Por esta razón, los datos Presence-Only no permiten estimar directamente probabilidades absolutas de ocupación sin imponer supuestos fuertes adicionales.

---

## 1.2 El Enfoque Presence-Background

Para inferir los requerimientos de hábitat utilizamos un diseño Presence-Background (relacionado con diseños de Caso-Control en epidemiología).

| Tipo de Punto | Definición | Variable |
|---|---|---|
| Presencia (Caso) | Registro confirmado en GBIF | $y_i = 1$ |
| Fondo (Background) | Puntos muestreados aleatoriamente del espacio disponible en Bogotá | $y_i = 0$ |

### Concepto Clave

Los puntos de fondo no representan ausencias biológicas reales.

Simplemente describen las condiciones ambientales disponibles en Bogotá. Al comparar las condiciones ambientales donde el Copetón fue observado contra las condiciones disponibles en el fondo, el modelo aprende qué variables ambientales están asociadas con una mayor o menor Idoneidad Ambiental Relativa (*Relative Environmental Suitability*).

En consecuencia, el modelo debe interpretarse como un modelo de:

- intensidad relativa de presencia,
- selección ambiental,
- o preferencia relativa de hábitat,

y no como una estimación directa de la probabilidad absoluta de ocupación.

---

## 1.3 Sampling Bias (Sesgo de Muestreo)

Las observaciones de GBIF son oportunistas y presentan sesgo espacial. Generalmente se concentran en:

- parques urbanos,
- zonas accesibles,
- áreas densamente pobladas,
- y regiones con mayor actividad de observadores.

Para reducir este problema y evitar que el modelo aprenda la distribución de los observadores en lugar de la distribución de la especie, aplicamos un procedimiento de:

### Spatial-Temporal Thinning (raleo espacio-temporal)

el cual reduce la autocorrelación y la sobre-representación de zonas altamente muestreadas.

---

# 2. El Modelo: Regresión Logística Bayesiana

En ecología moderna, este problema se modela frecuentemente mediante una Regresión Logística Bayesiana Presence-Background.

---

## 2.1 Distribución de la Respuesta (Likelihood)

Asumimos que la clasificación de cada punto como presencia o fondo sigue una distribución Bernoulli:

$$
y_i \sim \text{Bernoulli}(\psi_i)
$$

donde:

$$
\psi_i
$$

representa la intensidad relativa de presencia.

La relación entre:

$$
\psi_i
$$

y las covariables ambientales se modela usando una función de enlace logit:

$$
\psi_i = \frac{e^{\eta_i}}{1 + e^{\eta_i}}
$$

---

## 2.2 Predictor Lineal

El predictor lineal conecta las variables ambientales con la intensidad relativa de presencia:

$$
\eta_i =
\beta_0
+
\beta_{PM10} PM10_i
+
\beta_{O3} O3_i
+
\beta_{NO2} NO2_i
+
\beta_{CO} CO_i
+
\beta_{SO2} SO2_i
$$

donde:

- $\beta_0$ es el intercepto,
- $\beta_k$ representa el efecto de cada contaminante.

---

## 2.3 Escalamiento y Estandarización de Covariables

Idealmente, el modelo se ajustará inicialmente utilizando las covariables en sus unidades originales (por ejemplo: µg/m³ para contaminantes atmosféricos). Esto permite una interpretación ecológica más directa de los coeficientes:

- $\beta_k > 0$: incrementos en el contaminante aumentan la idoneidad relativa.
- $\beta_k < 0$: incrementos en el contaminante disminuyen la idoneidad relativa.

En este caso, el Odds Ratio:

$$
OR_k = e^{\beta_k}
$$

se interpreta como el cambio multiplicativo en la idoneidad relativa asociado a un incremento de una unidad física del contaminante.

Sin embargo, en modelos Bayesianos con algoritmos MCMC como NUTS, variables con escalas muy diferentes pueden generar:

- geometrías posteriores difíciles,
- mezclas lentas,
- divergencias,
- o problemas de convergencia.

Por esta razón, si el modelo presenta problemas computacionales (por ejemplo: divergencias, bajo ESS o $\hat{R} > 1.01$), se recurrirá a la estandarización de covariables:

$$
x^* = \frac{x - \mu}{\sigma}
$$

donde:

- $\mu$ es la media,
- $\sigma$ es la desviación estándar.

La estandarización:

- mejora la estabilidad numérica,
- facilita el muestreo MCMC,
- y permite comparar magnitudes relativas entre coeficientes.

En el caso de utilizar variables estandarizadas, los coeficientes pueden transformarse posteriormente nuevamente a la escala original para recuperar interpretabilidad ecológica:

$$
\beta_k^{(\text{original})}
=
\frac{\beta_k^{(\text{std})}}{\sigma_k}
$$

y el intercepto se ajusta mediante:

$$
\beta_0^{(\text{original})}
=
\beta_0^{(\text{std})}
-
\sum_k
\frac{\mu_k}{\sigma_k}
\beta_k^{(\text{std})}
$$

De esta manera, el análisis mantiene simultáneamente:

- estabilidad computacional,
- convergencia adecuada,
- e interpretabilidad ecológica final.

---

## 2.4 Multicolinealidad

Los contaminantes atmosféricos urbanos suelen estar correlacionados entre sí. Por ejemplo:

- tráfico vehicular puede emitir simultáneamente $NO_2$ y $CO$.

Por ello, antes del ajuste final evaluamos:

- matrices de correlación,
- y posiblemente el Variance Inflation Factor (VIF),

con el fin de verificar la identificabilidad de los coeficientes $\beta$.

---

# 3. Distribuciones A Priori (Priors)

Siguiendo la práctica estándar en modelos Bayesianos de regresión, utilizamos priors débilmente informativos:

$$
\beta_k \sim N(0,1)
\qquad \forall k
$$

Estos priors:

- permiten efectos desde pequeños hasta moderadamente fuertes,
- regularizan el modelo,
- y evitan que el algoritmo explore valores extremos poco plausibles.

---

## 3.1 El Intercepto ($\beta_0$)

En modelos Presence-Background, el intercepto generalmente no tiene una interpretación ecológica directa.

Esto ocurre porque absorbe:

- la prevalencia desconocida de la especie,
- la fracción de muestreo,
- y parte del sesgo de observación.

Por esta razón:

- el interés principal del análisis se centra en los coeficientes ambientales $\beta_k$,
- y no en interpretar $\beta_0$ como una probabilidad absoluta de ocupación.

Este enfoque sigue las recomendaciones de la literatura moderna Presence-Only, la cual enfatiza que los datos Presence-Background permiten estimar de forma robusta:

- efectos relativos,
- relaciones ambientales,
- y patrones de selección de hábitat,

sin requerir estimaciones directas de prevalencia absoluta.

---

# 4. Contexto Teórico Adicional (Opcional)

Existen extensiones más complejas para Presence-Only en la literatura ecológica.

---

## 4.1 Latent Occupancy Augmentation

Algunos modelos introducen variables latentes:

$$
Z_j \sim \text{Bernoulli}
$$

para intentar imputar el verdadero estado biológico de los puntos de fondo.

Aunque teóricamente rigurosos, estos enfoques suelen introducir:

- problemas de identificabilidad,
- mezclas lentas en MCMC,
- y dificultades computacionales importantes.

---

## 4.2 Inhomogeneous Poisson Process (IPP)

Renner & Warton (2013) demostraron que la regresión logística Presence-Background aproxima un:

### Inhomogeneous Poisson Process (IPP)

cuando se utilizan suficientes puntos de fondo.

---

## 4.3 Pólya-Gamma

Otros enfoques utilizan aumentación Pólya-Gamma para:

- linealizar el logit,
- y acelerar algoritmos Gibbs.

Sin embargo, gracias al algoritmo NUTS utilizado por PyMC, estas técnicas no son necesarias para nuestro caso.

---

# 5. Implementación del Modelo en PyMC

```python
import pymc as pm
import numpy as np

# X: matriz de covariables
# y_obs: vector binario (1 = presencia, 0 = fondo)

with pm.Model() as bayesian_pb_model:

    # Priors para efectos ambientales
    beta = pm.Normal(
        "beta",
        mu=0,
        sigma=1,
        shape=X.shape[1]
    )

    # Prior para intercepto
    beta_0 = pm.Normal(
        "beta_0",
        mu=0,
        sigma=2
    )

    # Predictor lineal
    eta = beta_0 + pm.math.dot(X, beta)

    # Función logística
    psi = pm.math.invlogit(eta)

    # Likelihood Presence-Background
    obs = pm.Bernoulli(
        "obs",
        p=psi,
        observed=y_obs
    )

    # Muestreo MCMC usando NUTS
    trace = pm.sample(
        draws=2000,
        tune=1000,
        target_accept=0.9,
        return_inferencedata=True
    )
```

---

# 6. Interpretación de la Inferencia Posterior

Al finalizar el muestreo MCMC obtenemos distribuciones posteriores completas para cada coeficiente $\beta_k$.

| Medida Posterior | Interpretación |
|---|---|
| Mediana Posterior | Efecto ambiental más probable |
| HDI 95% | Intervalo de credibilidad Bayesiano |
| $\beta_k < 0$ | Evidencia de efecto negativo |
| $\beta_k > 0$ | Evidencia de asociación positiva |
| $OR_k = e^{\beta_k}$ | Cambio multiplicativo en la idoneidad relativa |

---

## Odds Ratio

$$
OR_k = e^{\beta_k}
$$

Interpretación:

- por cada aumento de una unidad del contaminante,
- la idoneidad relativa se multiplica por $OR_k$.

---

# 7. Interpretación Ecológica Final

Este modelo permite identificar:

- qué contaminantes están asociados con mayor o menor presencia relativa del Copetón,
- cuáles variables ambientales tienen efectos más importantes,
- y cómo cambia la idoneidad relativa del hábitat en Bogotá.

Es importante enfatizar que:

> el modelo estima patrones relativos de selección ambiental, no probabilidades absolutas de ocupación, debido a la naturaleza Presence-Only de los datos.

### Formas Correctas de Interpretar los Resultados

Dado que la regresión logística Presence-Background aproxima un Proceso de Poisson Inhomogéneo (IPP), lo que realmente estamos midiendo es la **intensidad de puntos**. A continuación se presentan ejemplos de cómo frasear e interpretar correctamente los coeficientes durante la sustentación del proyecto:

1. **Sobre la Probabilidad Relativa:**
   * *"El $PM_{10}$ reduce la probabilidad relativa de presencia."*
   * **Qué significa:** Comparado con el promedio ambiental de la ciudad (el fondo), es menos probable encontrar al copetón allí.

2. **Sobre la Asociación con Registros:**
   * *"Existe una asociación negativa entre el contaminante y los registros de presencia."*

3. **Sobre la Intensidad de Presencia (Enfoque IPP):**
   * *"Las zonas con alta concentración de $O_3$ muestran una menor intensidad de presencia."*
   * **Qué significa:** Imagínelo como una "densidad de registros": en las zonas donde hay más contaminación, los registros están más "esparcidos" o son más escasos, indicando un declive en la idoneidad del hábitat.

---

# Referencias Conceptuales Clave

- Golini, N. (2013). *Bayesian analysis of presence-only data.*
- Ward, G. et al. (2009). *Presence-only data and logistic regression.*
- Fithian, W. & Hastie, T. (2013). *Finite-sample equivalence in statistical models for presence-only data.*
- Renner, I. & Warton, D. (2013). *Equivalence of MAXENT and Poisson point process models.*