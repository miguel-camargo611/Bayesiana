# Guía Teórica: Construcción de la Posterior en Modelos de Ocupación

Esta guía detalla el proceso matemático y logístico para construir un modelo Bayesiano de ocupación jerárquico, enfocado en el cruce de datos de aves y contaminación.

## 1. El Fundamento: El Teorema de Bayes

La meta de cualquier análisis Bayesiano es hallar la **Distribución Posterior** de los parámetros ($\theta$), dado que hemos observado ciertos datos ($D$):

$$P(\theta | D) = \frac{P(D | \theta) P(\theta)}{P(D)}$$

Donde:
- $P(D | \theta)$ es la **Likelihood** (Verosimilitud): ¿Qué tan probables son los datos según mis parámetros?
- $P(\theta)$ es la **Prior**: Mi conocimiento o suposición inicial sobre los parámetros.
- $P(D)$ es la evidencia (una constante de normalización que suele ignorarse en el muestreo).

---

## 2. Paso a Paso de la Construcción

### Paso 1: Definir la Likelihood del Sistema Completo
En un modelo de ocupación, tenemos dos tipos de parámetros: $\beta$ (para ocupación) y $\alpha$ (para detección), además de un estado latente $z$ (presencia real).

La **Likelihood Total** es la probabilidad conjunta de observar lo que vimos en eBird ($y$) dado el estado de ocupación ($z$) bajo los parámetros $\alpha$ y $\beta$:

$$L(y, z | \beta, \alpha) = \prod_{i=1}^N \underbrace{P(z_i | \beta)}_{\text{Ocupación}} \cdot \underbrace{\prod_{j=1}^{K_i} P(y_{i,j} | z_i, \alpha)}_{\text{Detección}}$$

- **Ocupación**: $z_i \sim \text{Bernoulli}(\text{logit}^{-1}(X_i\beta))$. Si el sitio está contaminado, $\psi_i$ baja.
- **Detección**: $y_{i,j} \sim \text{Bernoulli}(z_i \cdot \text{logit}^{-1}(W_{i,j}\alpha))$. Si no hay ave ($z_i=0$), no detectamos nada.

### Paso 2: Definir las Priors (Informativas vs No Informativas)
Para cada coeficiente de nuestras regresiones, asignamos una distribución previa. 

$$P(\beta, \alpha) = P(\beta) \cdot P(\alpha)$$

Comúnmente se usan **Normales Multivariadas**:
$$\beta \sim \text{MVN}(\mu_\beta, \Sigma_\beta)$$
$$\alpha \sim \text{MVN}(\mu_\alpha, \Sigma_\alpha)$$

- Si pones una varianza ($\Sigma$) muy grande, la prior es "plana" y dejas que los datos decidan.
- El modelo de **Clark (2019)** usa estas priors para estructurar los efectos de los contaminantes.

### Paso 3: Combinar Likelihood y Prior para la Posterior
Multiplicamos ambos componentes. La distribución posterior conjunta es:

$$P(\beta, \alpha, \mathbf{z} | \mathbf{y}) \propto \left[ \prod_{i=1}^N \text{Bern}(z_i | \psi_i) \prod_{j=1}^{K_i} \text{Bern}(y_{i,j} | z_i p_{i,j}) \right] \cdot P(\beta) \cdot P(\alpha)$$

### Paso 4: El Desafío del Logit y la Solución de Clark (Polya-Gamma)
Como el término logit hace que la posterior no tenga una forma fácil de integrar, Clark introduce variables de aumento **Polya-Gamma ($\omega$)**. 

Esto transforma la Likelihood Bernoulli en una forma que parece una Normal. El paso a paso computacional (Gibbs Sampling) sería:
1.  **Actualizar $z$**: Estimar si el ave estaba presente en sitios donde no se vio.
2.  **Actualizar $\omega$**: Generar las variables latentes de Polya-Gamma.
3.  **Actualizar $\beta$ y $\alpha$**: Al usar $\omega$, la posterior de los coeficientes se convierte en una **Normal**, que es muy fácil de calcular:
    $$\theta_{post} \sim \text{Normal}(\text{Media Ponderada}, \text{Varianza Actualizada})$$

---

## 3. Resultado Final: Los Parámetros Posteriores
Al final del proceso, el modelo te devuelve miles de muestras de la "Posterior". Para cada contaminante tendrás:
1.  **Estimación puntual**: La media o mediana de la posterior.
2.  **Incertidumbre**: Intervalos de Credibilidad (p.ej., del 95%). 

**Interpretación Biológica:**
Si el intervalo de credibilidad del coeficiente de `pm25_ugm3` no incluye al cero y es negativo, habrás demostrado que el material particulado reduce significativamente la probabilidad de ocupación de esa especie en Bogotá.
