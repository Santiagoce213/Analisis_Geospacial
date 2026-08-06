# Contexto del proyecto v2 — Análisis Geoespacial: Altiplanos

> Continuación de `CONTEXTO_PROYECTO.md` (que queda intacto como histórico de la primera
> etapa). Este archivo documenta la **regeneración** de los notebooks de análisis siguiendo
> las skills del proyecto (`notebook-analisis-reproducible`, `exploracion-datos-previa-modelo`,
> `metricas-evaluacion-prediccion`, `actualizar-contexto-tras-ejecucion`).
> Última actualización: 2026-08-04 (NB09b Sección 3 evaluada a 50 m).

## 0. Por qué existe este archivo y qué cambió respecto a la v1

- El usuario pidió regenerar todos los notebooks de `Codigo\` (excepto los que resultaran
  ser puramente "de corrección") aplicando las condiciones de las skills: notebooks
  reales (`.ipynb`, nunca `.py`), estructura celda-a-celda (markdown explicativo antes/después
  de cada bloque de código), sección de exploración de datos con histogramas antes de
  cualquier modelo, tabla de métricas completa por modelo, y reporte explícito de vecinos
  faltantes ("islas") en las matrices de pesos por distancia.
- **Decisión de consolidación:** `03b_regresion_no_espacial_matriz_corregida.ipynb`,
  `06_mapas_clusters_n_mayor_3.py` y `07_perfil_clusters_n_mayor_3.py` eran correcciones/parches
  sobre `03`, `01` y `02` respectivamente (ver `CONTEXTO_PROYECTO.md` para su contenido original).
  En vez de regenerarlos como archivos separados, su lógica se **incorporó directamente** en
  los notebooks `_v2` correspondientes:
  - La matriz de confusión normalizada por fila de `03b` → dentro de `03_..._v2.ipynb`.
  - El criterio "mejor Silhouette con n_clusters ≥ 4" (en vez de `K_ELEGIDO=4` fijo a mano)
    de `06`/`07` → dentro de `01_..._v2.ipynb` y `02_..._v2.ipynb`.
  - Resultado: **6 notebooks nuevos** en vez de 9 archivos.
- **Archivos originales (v1): NO se modifican ni se borran.** Los notebooks/scripts `01`-`05`,
  `03b`, `06`, `07` y `Clustering_Regiones.ipynb` quedan intactos en `Codigo\` como referencia
  histórica. Las capas (`.gpkg`/`.tif`) que ya existían en `Resultados\` tampoco se tocan.
- **Convención de nombres nueva (solo para v2):**
  - Notebooks: sufijo `_v2` (ej. `01_clustering_altiplanos_v2.ipynb`).
  - Imágenes nuevas: `Resultados\<nombre_notebook_v2>\NN_descripcion.png` (carpeta propia por
    notebook, en vez del listado plano `Resultados\NN_descripcion.png` de la v1).
  - Capas nuevas (`.gpkg`/`.tif`): mismo nombre que la v1 + sufijo `_v2`, en la raíz de
    `Resultados\` (para no chocar con las capas ya existentes, que un notebook v2 posterior
    podría necesitar leer sin ambigüedad).

## 1. Estado de la regeneración (ir marcando conforme se complete)

| # | Notebook v2 | Estado | Notas |
|---|---|---|---|
| 1 | `01_clustering_altiplanos_v2.ipynb` | ✅ listo (ejecutado sin errores) | K_ELEGIDO=7 |
| 2 | `02_clustering_espacial_altiplanos_v2.ipynb` | ✅ listo (ejecutado sin errores) | radio ganador=7.4 km, 10% islas |
| 3 | `03_regresion_no_espacial_raster_v2.ipynb` | ✅ listo (ejecutado sin errores) | AUC=0.9522, PseudoR2=0.5514 |
| 4 | `04_autocorrelacion_espacial_v2.ipynb` | ✅ listo (ejecutado sin errores) | Moran I residuos=0.610 |
| 5 | `05_modelo_jerarquico_cordilleras_v2.ipynb` | ✅ listo (ejecutado sin errores) | AUC=0.9522, recall=0.92 |
| 6 | `Clustering_Regiones_v2.ipynb` | ✅ listo (ejecutado sin errores) | K_REGIONES=4 |

## 2. Trabajo realizado — resumen por archivo (v2)

### `01_clustering_altiplanos_v2.ipynb` — Clustering NO espacial de los 491 altiplanos (v2)
- Ejecutado de punta a punta con `jupyter nbconvert --execute`, 40 celdas, 0 errores.
- **Nuevo respecto a la v1:** sección de exploración de datos (estadísticas descriptivas,
  histogramas de Altitud_X/Relieve_X/Pend_X, área total y promedio de los 491 polígonos:
  Área total ≈ suma de la columna `Área`, contrastada contra `geometry.area`; N=491, sin
  exclusiones por NoData al ser datos vectoriales).
- **Selección de K consolidada** (incorpora el criterio de `07_perfil_clusters_n_mayor_3.py`,
  ya no es un archivo aparte): mejor Silhouette con `n_clusters >= 4` → **K_ELEGIDO=7**
  (SS=0.284), vs. el óptimo global sin restricción en k=2 (SS=0.401, descartado por no ser
  geomorfológicamente útil). **Este valor difiere del K_ELEGIDO=4 fijado a mano en la v1** —
  cualquier comparación con el trabajo anterior debe tener esto en cuenta.
- Reparto de los 491 polígonos entre los 7 clusters (K-means): tamaños entre 9 y 118
  polígonos (más pequeño: cluster 1 con 9; más grandes: clusters 4 y 6 con 118 cada uno).
- Exports: `Resultados\altiplanos_clasificados_v2.gpkg`. Figuras en
  `Resultados\01_clustering_altiplanos_v2\` (7 PNG: histogramas, correlación, selección de
  k, dendrograma, mapa de clusters, heatmap de perfil, DTW vs. K-means).

### `02_clustering_espacial_altiplanos_v2.ipynb` — Clustering con restricción espacial (v2)
- Ejecutado de punta a punta con `jupyter nbconvert --execute`, 39 celdas, 0 errores.
- **Nuevo respecto a la v1:** histograma de distancia al vecino más cercano (sección de
  exploración); `K_ELEGIDO` recalculado con el mismo criterio de `01_..._v2` (self-contained,
  no depende de correr 01 primero) → **K_ELEGIDO=7** (coincide con 01_v2); la búsqueda del
  "mejor" (vecindad, n_clusters) en la grilla completa ahora también restringe
  `n_clusters >= 4` (antes solo restringía el baseline, consolidando aquí el criterio de
  `06_mapas_clusters_n_mayor_3.py`).
- **Reporte explícito de polígonos sin vecinos (pedido por el usuario):** nueva sección [7]
  dedicada con tabla + gráfico de barras — para el radio con mejor SS global (7.4 km),
  **49 de 491 polígonos (10.0%) quedan sin ningún vecino** (83 componentes desconectados en
  el grafo de conectividad). El notebook imprime una advertencia explícita cuando esto
  ocurre. Confirmado también que **KNN nunca deja polígonos sin vecinos**, por construcción.
- **Resultados de la búsqueda (con K_ELEGIDO=7 recalculado, difieren de la v1 que usaba
  K_ELEGIDO=4):**
  - Línea base sin restricción espacial: SS=0.211.
  - Mejor KNN: k=8, n_clusters=4, SS=0.260.
  - Mejor DistanceBand: radio=7.4 km, n_clusters=4, SS=0.285 (ganador global), con la
    advertencia de 10% de islas ya mencionada.
  - ARI (ganadora vs. sin restricción): 0.226 — la restricción espacial sí reorganiza
    sustancialmente la tipología, no es cosmético.
  - Diagnóstico geográfico: distancia promedio intra-cluster (139.6 km) < inter-cluster
    (157.9 km) → los altiplanos del mismo tipo sí tienden a estar más cerca entre sí.
- Exports: `Resultados\altiplanos_clustering_espacial_v2.gpkg`. Figuras en
  `Resultados\02_clustering_espacial_altiplanos_v2\` (8 PNG).

### `03_regresion_no_espacial_raster_v2.ipynb` — Regresión logística a nivel de píxel (v2)
- Ejecutado de punta a punta con `jupyter nbconvert --execute`, 38 celdas, 0 errores.
- **Nuevo respecto a la v1:** sección de exploración de datos explícita (N total=50,351,184
  píxeles; válidos según DEM=24,814,468 (49.3%); excluidos además por NoData en algún
  predictor=30,502 (0.1%); válidos finales=24,783,966 (49.2%); área cubierta por la grilla
  completa=125,878.0 km², área válida usada en el modelo=61,959.9 km²; histogramas de
  Altitud/Pendiente/Relieve_5/ResidMax_10 separados por clase de la variable respuesta).
  Matriz de confusión ahora en **3 paneles** (conteos + normalizada por fila + ROC),
  consolidando `03b_regresion_no_espacial_matriz_corregida.ipynb` directamente aquí.
- **Resultados (idénticos a la v1, como se esperaba — mismo pipeline determinista con
  SEMILLA=42):** Pseudo R² (McFadden)=0.5514, AIC=79934.6, BIC=80129.5, AUC-ROC=0.9522,
  Accuracy=0.9124. Recall Altiplano=64.5%, Recall No altiplano=96.0% (con umbral 0.5, sin
  balanceo de clases — se retoma con `class_weight="balanced"` en el notebook 05).
  Advertencia de cuasi-separación completa de `statsmodels` documentada igual que en la v1.
- Exports: `Resultados\probabilidad_altiplano_v2.tif`. Figuras en
  `Resultados\03_regresion_no_espacial_raster_v2\` (4 PNG).

### `04_autocorrelacion_espacial_v2.ipynb` — Moran's I y LISA (v2)
- Ejecutado de punta a punta con `jupyter nbconvert --execute`, 39 celdas, 0 errores.
- **Nuevo respecto a la v1:** exploración de datos breve en ambas partes (histogramas de
  Altitud_X/Pend_X/Relieve_X en Parte A; N y área de la muestra de 300k píxeles documentados
  explícitamente en Parte B). Lee `altiplanos_clustering_espacial_v2.gpkg` (salida del
  notebook 02_v2) en vez de la capa v1.
- **Resultados (idénticos a la v1, mismo pipeline determinista):** Parte A — Moran's I:
  Altitud_X=0.920, Pend_X=0.589, Relieve_X=0.484 (todos p=0.001); 284/491 polígonos (58%) en
  clúster LISA significativo. Parte B — Moran's I de residuos=0.610 (p=0.001, z=676.43),
  confirmando autocorrelación espacial fuerte sin explicar en el modelo no espacializado.
- Exports: `Resultados\altiplanos_moran_lisa_v2.gpkg`,
  `Resultados\residuos_raster_lisa_muestra_v2.gpkg`. Figuras en
  `Resultados\04_autocorrelacion_espacial_v2\` (6 PNG).

### `05_modelo_jerarquico_cordilleras_v2.ipynb` — Modelo jerárquico por cordillera (v2)
- Ejecutado de punta a punta con `jupyter nbconvert --execute`, 37 celdas, 0 errores.
- **Nuevo respecto a la v1:** exploración de datos con histogramas de Altitud/Pendiente por
  zona (además de la tabla de proporción de Altiplano por zona ya existente); la tabla de
  métricas del modelo jerárquico bayesiano ahora se extrae explícitamente (fila `Zona`:
  media posterior, SD, IC) en vez de solo imprimir el `.summary()` crudo.
- **Resultados (idénticos a la v1, mismo pipeline determinista):** proporción de Altiplano
  por zona: Occidental=3.8%, Central=25.2%, SanLucas=16.9%. Comparación 2x2: AUC≈0.952 en
  las 4 combinaciones; balanceo de clases sube recall de Altiplano de 0.645→0.917 (sin zona)
  y 0.648→0.919 (con zona). Modelo operativo final: AUC=0.9522, Accuracy=0.865,
  Recall(Altiplano)=0.92, Precision(Altiplano)=0.53. Modelo jerárquico bayesiano: SD del
  intercepto aleatorio por zona=0.226, IC=[0.083, 0.612] (no incluye 0 → heterogeneidad real
  entre cordilleras confirmada estadísticamente).
- Exports: `Resultados\zonas_cordilleras_v2.tif`,
  `Resultados\probabilidad_altiplano_jerarquico_v2.tif`,
  `Resultados\muestra_modelo_jerarquico_v2.gpkg`. Figuras en
  `Resultados\05_modelo_jerarquico_cordilleras_v2\` (4 PNG).

### `Clustering_Regiones_v2.ipynb` — Regionalización contigua para el modelo jerárquico (v2)
- Ejecutado de punta a punta con `jupyter nbconvert --execute`, 36 celdas, 0 errores.
- **Nuevo respecto a la v1:** sección de exploración de datos explícita al inicio
  (histogramas de Altitud/Pendiente/Relieve_Relativo sobre una muestra de 200,000 píxeles
  válidos de la grilla nativa de 50 m; N=24,783,966 píxeles válidos, área=61,959.9 km²);
  introducción reescrita para aclarar explícitamente el propósito de este cluster **de
  píxeles** (construir zonas con distribución/características distintas para el modelo
  jerárquico) frente a los clusters **de altiplanos** de los notebooks 01/02.
- **Resultados (idénticos a la v1, mismo pipeline determinista):** grilla agregada a 1 km
  (413x304=125,552 celdas, 61,950 válidas). K_REGIONES=4 (SS=0.065 con k≥4; óptimo sin
  restricción en k=2, SS=0.191, descartado). Proporción de Altiplano por región: 0=18.8%,
  1=0.2%, 2=12.1%, 3=26.8%. Rango entre zonas (max-min)=0.266, mayor que el de las 3
  Cordilleras (0.214) → esta zonificación separa mejor el fenómeno de interés.
- Exports: `Resultados\zonas_clustering_regiones_v2.tif`,
  `Resultados\regiones_clustering_v2.gpkg`,
  `Resultados\zonas_clustering_regiones_v2_k15.tif`,
  `Resultados\regiones_clustering_v2_k15.gpkg`. Figuras en
  `Resultados\Clustering_Regiones_v2\` (8 PNG).

## 3. Modelos del libro pendientes — factibilidad con los datos actuales (2026-07-17)

Los 6 notebooks quedaron regenerados y ejecutados sin errores (ver sección 1). Evaluación
de factibilidad de los métodos candidatos del libro contra los datos y el entorno técnico
disponibles HOY:

| Método del libro | ¿Factible ya? | Con qué datos | Qué falta |
|---|---|---|---|
| `10_SAR` (SLX/SEM/SAR-Lag) | **✅ Completado** (`10_SAR_altiplanos_v2.ipynb`) | 491 altiplanos + pesos KNN(k=6) | — |
| `03_PointPattern` (centrografía, KDE, Ripley G/F, DBSCAN) | **✅ Completado** (`03_PointPattern_altiplanos_v2.ipynb`) | 491 centroides de altiplano como patrón de puntos puro | — |
| `13_MGWR` (GWR/MGWR) | **✅ Completado** (`13_MGWR_altiplanos_v2.ipynb`) | 491 centroides + predictores ya usados en `10_SAR_v2` | — |
| `11_CAR` (ICAR/BYM/Leroux) | **✅ Completado** (`11_CAR_altiplanos_v2.ipynb`, vía CARBayes) | Grilla areal de **5 km** (~2.596 celdas, contigüidad Rook real) derivada de los rásters; región de `Clustering_Regiones_v2` como covariable | — (INLA sigue bloqueado en Windows, pero la ruta CARBayes cubre el método) |

## 4b. Ronda de correcciones pedidas por el usuario (2026-07-17, tras revisión de resultados)

El usuario revisó las figuras/modelos generados y pidió varias correcciones. Estado:

1. **Quitar Calinski-Harabasz (CH) de todo el proyecto** — confirmado que NO es del libro
   (ya estaba anotado así en `CONTEXTO_PROYECTO.md` v1). Retirado de `01_v2` (import, barrido
   de k, panel del gráfico), `02_v2` (heatmaps 05/06 eliminados, búsqueda del "mejor" ya no
   usa CH) y `Clustering_Regiones_v2` (barrido de k, panel del gráfico). Solo queda
   método del codo + Silhouette en los tres, que sí son los criterios del libro
   (`08_ClusterEspacial`). **Re-ejecutados y verificados los 3 notebooks, 0 errores.**
2. **Quitar TimeSeriesKMeans/DTW de `01_v2`** — retirado por completo (código, gráfico,
   import de `tslearn`, texto). Justificación documentada en las conclusiones del notebook:
   DTW no aporta nada cuando no existe un eje secuencial real entre las variables (las 9
   variables morfométricas no tienen orden natural), y euclidiano ya superaba a DTW en las
   pruebas previas. Figura huérfana `06_dtw_vs_kmeans.png` borrada de
   `Resultados\01_clustering_altiplanos_v2\`.
3. **Redondear radios de `DistanceBand` a múltiplos de 0.5 km** en `02_v2` — nueva función
   `redondear_medio_km()`. Radios candidatos ahora: `[3.5, 4.0, 5.0, 5.5, 7.5, 10.0, 15.0,
   28.0]` km (antes tenían decimales arbitrarios tipo 7.4, 3.7). El radio ganador cambió a
   **5.0 km** (antes 7.4 km), con **132/491 (26.9%) polígonos sin vecinos** — más alto que
   antes porque el candidato más cercano disponible ahora es 5.0 km en vez de 3.7 km; sigue
   reportado con la misma advertencia explícita.
4. **Usar `Capas\Regiones.shp`** (4 polígonos, mismo resultado K=4 de `Clustering_Regiones_v2`
   pero con nombres agregados a mano por el usuario en el campo `Regiones`:
   "Cordillera Central - Magdalena", "Cordillera Occidental - Farallones",
   "Cordillera Occidental - Atrato", "Cordillera Central - Altiplanos") como segunda
   zonificación del modelo jerárquico, en paralelo a `Cordilleras.shp` — **pendiente de
   implementar en `05_v2`**.
5. **Métricas de `03_v2` centradas en la clase Altiplano**, no en "No altiplano" —
   **✅ implementado** (función `reportar_metricas_y_graficar()` reutilizable, imprime
   recall/precision/F1 de Altiplano primero y con más énfasis, Accuracy y métricas de
   "No altiplano" quedan como referencia secundaria).
6. **Segundo modelo no espacial (GLM Binomial cloglog) — implementado y luego RETIRADO por
   instrucción del usuario.** Se documenta aquí la explicación completa para no perderla:
   - **Por qué NO binomial negativa:** modela conteos (0,1,2,3...) con noción de exposición
     (área/tiempo); no es aplicable directamente a una respuesta binaria 0/1 por píxel sin
     antes agregar a alguna unidad espacial (lo cual cambiaría la pregunta de "¿es este
     píxel altiplano?" a "¿cuántos píxeles altiplano hay en esta zona?").
   - **Qué es cloglog:** GLM de la misma familia Binomial que logit (`04_GLMPhyton`), solo
     cambia la función de enlace: $g(\pi)=\log(-\log(1-\pi))$, la CDF de la distribución
     Gumbel (valores extremos) en vez de la CDF logística. A diferencia de logit/probit
     (simétricos alrededor de p=0.5), cloglog es **asimétrico**: sube muy lento desde 0 y
     muy rápido hacia 1. Surge naturalmente como el análogo en tiempo discreto de un modelo
     de riesgos proporcionales (Cox) — por eso sus coeficientes se interpretan como razones
     de tasa/riesgo ($e^{\beta_k}$), no como odds ratios. Es la razón por la que se usa en
     modelos de presencia/ausencia en ecología (fenómenos raros, igual que Altiplano=15.1%).
   - **Resultado obtenido antes de retirarlo** (test set, N=90,000, sin zona):
     Pseudo R²: logit=0.5514 vs. cloglog=0.5476; AIC: 79,934.6 vs. 80,615.3 (logit mejor);
     AUC: 0.9522 vs. 0.9520 (casi iguales, esperado — el AUC mide *ranking*, no el punto de
     corte); **Recall Altiplano: 0.645 vs. 0.599 (logit mejor); Precision Altiplano: 0.740
     vs. 0.767 (cloglog mejor)** — cloglog es más "exigente" antes de predecir Altiplano
     (menos falsos positivos, pero también se le escapan más altiplanos reales).
   - **Bug real encontrado y corregido mientras estuvo implementado** (por si se retoma en
     el futuro): `modelo_cloglog.llf` daba `NaN` en `statsmodels` porque algunas
     probabilidades ajustadas caen en exactamente 1.0 en punto flotante (dada la
     cuasi-separación ya señalada para logit), y `log(1-mu)=log(0)` rompe el cálculo interno
     de `.llf`. Solución: para observaciones Bernoulli individuales, `Deviance = -2*llf`
     exactamente, así que Pseudo R²/AIC/BIC se pueden recalcular desde `.deviance` (que sí
     sale finito) en vez de `.llf`.
   - **Decisión final (2026-07-17):** el usuario pidió quitar este modelo de `03_v2` y
     volver a un solo modelo (logit). `03_v2` fue revertido a su forma de un solo modelo;
     esta entrada queda como registro de lo explorado por si se retoma más adelante.
7. **Diagnóstico del AUC casi idéntico** — **✅ confirmado que NO es un bug.** Se ajustaron 4
   modelos sobre la misma muestra/partición y se imprimió el AUC a 6 decimales: sin zona sin
   balancear=0.953145, sin zona balanceado=0.953178 (difieren en la 4ª cifra, no son
   idénticos bit a bit). La correlación de Spearman entre las probabilidades balanceado vs.
   sin balancear es 0.9993 — `class_weight="balanced"` desplaza el intercepto/umbral (por
   eso cambian tanto el recall/precisión) pero apenas reordena las probabilidades relativas
   (por eso el AUC, que solo mide ese orden, casi no se mueve). Documentado explícitamente
   en el notebook con esta evidencia.
8. **Capacidad de predicción por zona** — **✅ implementado**, ver hallazgos en la sección 5b
   abajo.

### `03_regresion_no_espacial_raster_v2.ipynb` — Corrección (2026-07-17)
- Re-ejecutado de punta a punta, 44 celdas, 0 errores tras la corrección.
- Histograma de exploración rehecho: panel 1 = conteo total por clase (barras 0/1 con % en
  la población completa), paneles 2-4 = Altitud/Pendiente/Relieve_5 por clase (muestra de
  200,000). Reemplaza el histograma anterior que incluía ResidMax_10 en vez del conteo total.
- Métricas reportadas ahora vía función reutilizable `reportar_metricas_y_graficar()`
  (mismo diseño de figura de 3 paneles para cualquier modelo), enfocada en Altiplano.
- **Segundo modelo agregado: GLM Binomial con enlace cloglog** (Modelo 2), comparado
  explícitamente contra el logit estándar (Modelo 1) en una tabla lado a lado.
  - **Bug real encontrado y corregido:** `modelo_cloglog.llf` (log-verosimilitud) salía
    `NaN` de `statsmodels` — algunas probabilidades ajustadas con cloglog caen en
    exactamente 1.0 en punto flotante (dada la fuerte cuasi-separación ya señalada para
    logit), y `log(1-mu)=log(0)` rompe el cálculo interno de `.llf`/`.aic`/`.bic` de
    `statsmodels` para este enlace, aunque el ajuste en sí (coeficientes, deviance) sea
    válido. Solución: para observaciones Bernoulli individuales, `Deviance = -2*llf`
    exactamente (log-verosimilitud del modelo saturado es 0), así que Pseudo R²/AIC/BIC se
    recalculan a partir de `.deviance` (que sí sale finito) en vez de `.llf`.
  - **Resultado de la comparación (test set, N=90,000):** Logit vs. Cloglog — Pseudo
    R²=0.5514 vs. 0.5476; AIC=79,934.6 vs. 80,615.3 (logit mejor); AUC=0.9522 vs. 0.9520
    (prácticamente iguales, como se esperaba — el AUC mide *ranking*, no el punto de corte);
    Recall Altiplano=0.645 vs. 0.599 (logit mejor); **Precision Altiplano=0.740 vs. 0.767
    (cloglog mejor)**. Conclusión: para este dataset, logit sigue siendo la mejor opción
    global (mejor AIC, recall y AUC), pero cloglog ofrece más precisión a costa de recall —
    un trade-off legítimo si el costo de falsos positivos importa más que el de falsos
    negativos.
- Exports sin cambios (`probabilidad_altiplano_v2.tif`).

### `03_regresion_no_espacial_raster_v2.ipynb` — Reversión (2026-07-17, mismo día)
- El usuario pidió quitar el modelo cloglog y volver a un solo modelo. Revertido a un único
  modelo (logit), 38 celdas, 0 errores. El razonamiento y los resultados de la comparación
  cloglog quedan documentados en la sección 4b, punto 6, por si se retoma en el futuro.
- Quedan: exploración de datos con métricas centradas en Altiplano (sin cambios), función
  `reportar_metricas_y_graficar()` (sin cambios, ahora se usa una sola vez).
- Figuras vueltas a los nombres simples: `02_matriz_confusion_roc.png`,
  `03_mapa_probabilidad_altiplano.png`. Archivos huérfanos de la iteración con cloglog
  borrados de `Resultados\03_regresion_no_espacial_raster_v2\`.

### `05_modelo_jerarquico_cordilleras_v2.ipynb` — Corrección mayor (2026-07-17)
- Reescrito para comparar DOS zonificaciones en paralelo (antes solo usaba Cordilleras.shp):
  **Cordilleras** (3 zonas geológicas fijas) vs. **Regiones** (`Capas\Regiones.shp`, 4 zonas
  del clustering K=4 de `Clustering_Regiones_v2` con nombres agregados a mano por el
  usuario). Re-ejecutado de punta a punta, 39 celdas, 0 errores.
- **Hallazgo principal — Regiones supera a Cordilleras en todo:**
  - Rango de proporción de Altiplano entre zonas: Cordilleras=0.214 vs. **Regiones=0.266**.
  - Modelo operativo (zona+balanceado) en el set de prueba: AUC 0.9534→**0.9621**,
    Recall Altiplano 0.920→**0.928**, Precision Altiplano 0.531→**0.557**,
    F1 0.673→**0.696**, Accuracy 0.867→**0.879** (todas las métricas mejoran con Regiones).
  - **Modelo jerárquico bayesiano — diferencia dramática:** SD del intercepto aleatorio
    Cordillera=0.270 (IC=[0.104, 0.702]) vs. **Región=3.436 (IC=[1.903, 6.202])** — la
    zonificación por clustering captura muchísima más heterogeneidad real entre zonas que
    las 3 Cordilleras geológicas.
- **Diagnóstico del AUC (sección [8]):** confirmado explícitamente que el parecido entre
  AUC del modelo jerárquico y el de `03_v2` NO es un bug — ver punto 7 de la sección 4b.
- **Capacidad de predicción por zona (nuevo, sección [9]):** el modelo NO predice igual en
  todas las zonas. Hallazgo notable: la zona **"Cordillera Occidental - Farallones"** (de
  Regiones) tiene muy pocos altiplanos en el set de prueba (48 de 22,889 píxeles) y ahí el
  recall cae a 0.479 y la precisión a 0.190 — mucho peor que el resto de zonas (recall
  0.87-0.96 en las otras 3 regiones). Por Cordillera, el peor desempeño relativo es en
  Occidental (recall=0.729, precision=0.386) — coherente con ser la zona con menor
  proporción base de Altiplano (3.8%) en ambos análisis.
- Exports (sufijo `_v2`, más `_region` para la nueva zonificación):
  `Resultados\probabilidad_altiplano_jerarquico_v2.tif` (Cordillera),
  `Resultados\probabilidad_altiplano_jerarquico_v2_region.tif` (Región),
  `Resultados\zonas_cordilleras_v2.tif`. Figuras en
  `Resultados\05_modelo_jerarquico_cordilleras_v2\` (5 PNG).
- **Nota:** ya no se exporta una capa de puntos de muestra (`muestra_modelo_jerarquico_v2.gpkg`
  de la iteración anterior fue borrada por quedar huérfana del código actual); se puede
  volver a agregar si se necesita reabrir la muestra sin recalcular.

## 4c. Modelos nuevos implementados (2026-07-17) — `10_SAR`, `03_PointPattern`, `13_MGWR`

Usuario decidió avanzar con los tres métodos factibles en Python, dejando `11_CAR` pausado.
`pointpats` (2.6.0) y `mgwr` (2.2.1, con dependencia `spglm` 1.1.0) instalados vía pip sin
problemas.

### `10_SAR_altiplanos_v2.ipynb` — Regresión espacial SAR (nuevo)
- Ejecutado de punta a punta, 34 celdas, 0 errores.
- Y = `Altitud_X` (mayor Moran's I en `04_v2`, I=0.920), X = `Pend_X`, `Relieve_X`
  (estandarizados), pesos KNN(k=6) (mismo que `04_v2`, para comparabilidad). 0 islas (KNN).
- **OLS baseline:** R²=0.195, **Moran's I de residuos=0.828 (p≈0)**, LM-error y LM-lag
  ambos masivamente significativos (p~1e-247) → controlar por pendiente/relieve NO explica
  la autocorrelación de la altitud, se justifica un modelo espacial.
- **SLX:** rezago espacial de Pend_X/Relieve_X agregado como predictor exógeno (OLS).
- **SEM (`GM_Error_Het`):** λ=0.962 (z=71.9, p≈0), Pseudo R²=0.191. Residuo bruto `.u` sigue
  con Moran's I=0.920 — **por diseño** (SEM absorbe la dependencia en la estructura del
  error, no en el residuo observable; documentado explícitamente en el notebook para que no
  se lea como una falla del modelo).
- **SAR-Lag (`GM_Lag`):** ρ=0.898 (z=27.8, p≈0), Pseudo R²=0.923. Residuos con Moran's
  I=0.074 (p=0.002) — reducción drástica frente al OLS (0.828→0.074), evidencia de que el
  término ρWy capturó bien la dependencia espacial en los valores ajustados.
- Nota metodológica documentada: AIC/Log-Likelihood de OLS no son comparables directamente
  contra SEM/SAR-Lag (estimadores GMM, no MLE, en esta implementación de `spreg`) — se usó
  Pseudo R² y Moran's I de residuos como métricas comparables entre los 4 modelos.
- Exports: `Resultados\altiplanos_sar_v2.gpkg`. Figuras en
  `Resultados\10_SAR_altiplanos_v2\` (2 PNG: histogramas, mapa comparativo de residuos
  OLS vs. SAR-Lag).

### `03_PointPattern_altiplanos_v2.ipynb` — Análisis de patrón de puntos (nuevo)
- Ejecutado de punta a punta, 34 celdas, 0 errores.
- Enfoque puramente geométrico: los 491 centroides de altiplano tratados como patrón de
  puntos sin atributos (a diferencia de `01_v2`/`02_v2`, que sí usan morfometría). Métodos
  de `03_PointPattern` del libro vía `pointpats` 2.6.0.
- **Exploración:** N=491, bounding box 287.3 km (E-O) x 377.2 km (N-S), área bbox=108,351 km².
- **Centrografía:** centro medio (501582, 754290), centro mediano (505640, 742088),
  separados **12.9 km** → distribución asimétrica (confirma "brazos"/concentraciones
  visibles en el scatter). Distancia estándar=124.1 km. Elipse de desv. estándar: eje
  mayor=163.9 km, eje menor=63.7 km, rotación=53.1°.
- **Extensión:** envolvente convexa (11 vértices) vs. forma alfa (`libpysal.cg.alpha_shape_auto`,
  alfa óptimo=43.2 km, área=45,791 km², **42.3% del área del bounding box** — el patrón real
  ocupa bastante menos que su caja envolvente).
- **KDE:** dos anchos de banda (Scott automático vs. 80 km fijo) para contrastar detalle
  local vs. tendencia regional suavizada.
- **Cuadrantes (`QStatistic`, grilla 4x4):** prueba χ² de uniformidad, **p=1.41e-112** →
  se rechaza rotundamente la distribución uniforme sobre el área de estudio.
- **Simulación de Poisson:** patrón aleatorio de referencia (mismo N, mismo dominio =
  la forma alfa observada) para comparación visual antes de G/F.
- **Función G de Ripley** (`distance_statistics.g_test`, support=40, con envolvente de
  simulación): curva observada por encima de la banda de simulaciones aleatorias →
  vecinos más cercanos anormalmente próximos = **agrupamiento**.
- **Función F de Ripley** (`distance_statistics.f_test`, mismos parámetros): curva
  observada por debajo de la banda de simulación → grandes huecos vacíos, consistente
  con **agrupamiento**.
- **Interpretación conjunta:** cuadrantes + G + F coinciden en patrón **agrupado**,
  consistente con la autocorrelación espacial ya documentada (`04_v2` Moran's I hasta
  0.92, `10_SAR_v2` ρ=0.898).
- **DBSCAN:** 6 combinaciones de `(eps, min_samples)` probadas explícitamente (eps en
  km redondos: 5/10/15/20, min_samples 3/5), tabla completa de clusters/ruido:

  | eps (km) | min_samples | clusters | ruido | % ruido |
  |---|---|---|---|---|
  | 5.0 | 3 | 39 | 206 | 42.0% |
  | 5.0 | 5 | 12 | 375 | 76.4% |
  | 10.0 | 3 | 15 | 31 | 6.3% |
  | 10.0 | 5 | 13 | 60 | 12.2% |
  | 15.0 | 5 | 7 | 18 | 3.7% |
  | 20.0 | 5 | 4 | 10 | 2.0% |

  Combinación elegida para el mapa final: **eps=10 km, min_samples=5 → 13 clusters,
  12.2% de ruido** (balance entre fragmentación excesiva y sobre-agregación).
- **Bug corregido durante el desarrollo:** `sns.kdeplot(bw_adjust=None, ...)` lanzaba
  `TypeError: unsupported operand type(s) for *: 'float' and 'NoneType'` porque
  `bw_adjust` de seaborn siempre debe ser numérico (no acepta `None`) — se corrigió
  usando `bw_method="scott"` vs. `bw_method=80_000/std` con `bw_adjust` implícito=1 en
  ambos casos, en vez de intentar anular `bw_adjust`. También `QStatistic.plot()` no
  acepta el argumento `ax` (crea su propia figura internamente vía `self.mr.plot()`) —
  se corrigió llamando `qstat.plot()` sin `ax` y redimensionando la figura activa con
  `plt.gcf().set_size_inches(...)` antes de guardar.
- Exports: `Resultados\altiplanos_point_pattern_v2.gpkg` (incluye columna `cluster_dbscan`).
  Figuras en `Resultados\03_PointPattern_altiplanos_v2\` (9 PNG: scatter, centrografía,
  extensión hull/alpha, KDE, cuadrantes, observado-vs-aleatorio, Ripley G, Ripley F,
  mapa DBSCAN).

### `13_MGWR_altiplanos_v2.ipynb` — GWR/MGWR sobre los altiplanos (nuevo)
- Ejecutado de punta a punta, 37 celdas, 0 errores.
- Mismos datos que `10_SAR_altiplanos_v2.ipynb` (491 centroides, Y=`Altitud_X`,
  X=[`Pend_X`,`Relieve_X`], todos estandarizados a media 0/sd 1) — elegido explícitamente
  en vez de la muestra de 300k píxeles de `03_v2`/`05_v2` porque la calibración de
  ancho de banda de GWR/MGWR es computacionalmente cara (validación cruzada tipo
  leave-one-out); N=491 es tratable (~7s GWR, ~100s MGWR en esta máquina), N=300k no lo es.
  Esto también permite comparar directamente contra los resultados de SAR.
- **OLS global (statsmodels, referencia):** R²=0.195, R² ajustado=0.192, AICc=1292.89
  (idéntico al de `10_SAR_altiplanos_v2.ipynb`, como se esperaba — mismos datos).
- **Calibración GWR (`Sel_BW`, kernel adaptativo bisquare):** ancho de banda óptimo=**48
  vecinos** (9.8% de los 491 altiplanos), elegido por minimización de AICc vía búsqueda
  de sección áurea.
- **GWR:** R²=0.922, R² ajustado=0.909, AICc=309.40, parámetros efectivos (traza de S)=69.96
  — reducción de AICc frente a OLS de **983.5 puntos** (mejora sustancial, >>10). R² local
  varía de -0.373 a 0.939 (mediana=0.616) — el modelo funciona claramente mejor en unas
  zonas que en otras, algo invisible en el R² único de OLS.
- **MGWR (`Sel_BW(multi=True)`, backfitting):** anchos de banda **distintos por variable**:
  Intercepto=11 vecinos (2.2%), Pend_X=59 vecinos (12.0%), Relieve_X=35 vecinos (7.1%) —
  el efecto de la pendiente varía más lentamente en el espacio (bandwidth más grande, más
  parecido a un efecto global) que el del relieve o el intercepto.
- **MGWR resultado final:** R²=0.976, R² ajustado=0.966, AICc=2.22 — el mejor de los tres
  modelos según AICc, mejorando incluso sobre GWR (309.40→2.22).
- **Tabla comparativa completa (misma tabla en el notebook):**

  | Modelo | R² | R² ajustado | AICc |
  |---|---|---|---|
  | OLS global | 0.195 | 0.192 | 1292.89 |
  | GWR (bw único=48) | 0.922 | 0.909 | 309.40 |
  | MGWR (bw por variable) | 0.976 | 0.966 | 2.22 |

- **Comparación metodológica con `10_SAR_altiplanos_v2.ipynb`** (documentada explícitamente
  en el notebook, sección [13]): SAR-Lag alcanza Pseudo R²=0.923 con coeficientes **fijos**
  + término autorregresivo ρWy explícito (ρ=0.898); MGWR alcanza R²=0.976 sin término
  autorregresivo, dejando que **los coeficientes mismos varíen** espacialmente. Ambos
  enfoques mejoran radicalmente sobre el OLS global (R²=0.195), confirmando desde dos
  ángulos metodológicos independientes que ignorar la estructura espacial produce un
  modelo mal especificado.
- Mapas generados: R² local de GWR, coeficientes locales de GWR filtrados por
  significancia (`filter_tvals`, alpha=0.05 ajustado), coeficientes locales de MGWR.
- Exports: `Resultados\altiplanos_mgwr_v2.gpkg` (incluye columnas de R² local y
  coeficientes locales GWR/MGWR). Figuras en `Resultados\13_MGWR_altiplanos_v2\`
  (4 PNG: histogramas, mapa R² local GWR, mapas coeficientes GWR, mapas coeficientes MGWR).

## 4d. Corrección SAR/MGWR: evaluación sobre la clasificación real Altiplano/No-Altiplano (2026-07-17)

**Motivo de la corrección (pedido explícito del usuario):** `10_SAR_altiplanos_v2.ipynb` y
`13_MGWR_altiplanos_v2.ipynb` modelan `Altitud_X` (continua) usando únicamente los 491
polígonos de altiplano ya delimitados — **nunca evalúan si el modelo distingue Altiplano de
No-Altiplano**, porque las 491 filas de esos notebooks SON todas altiplanos. Se crearon DOS
notebooks NUEVOS (los originales **no se modificaron**) que aplican las mismas familias de
modelo (SAR y GWR) sobre la **clasificación binaria real** (Altiplano=1/No-Altiplano=0)
usando la capa de celdas del ráster, el mismo problema de `03_v2`.

### `10_SAR_altiplanos_clasificacion_v2.ipynb` — SAR/Probit espacial sobre clasificación (nuevo)
- Ejecutado de punta a punta, 33 celdas, 0 errores. N_MUESTRA=300,000 (igual que `03_v2`),
  predictores reducidos a Altitud/Pendiente/Relieve_5 (subconjunto de los 18 de `03_v2`,
  elegido por tratabilidad de los cálculos de rezago espacial).
- **Limitación técnica que obliga a cambiar de estimador:** `spreg.GM_Lag`/`GM_Error_Het`
  requieren Y continua — no aplican a un target binario. Se usa `spreg.Probit`, extendido de
  dos formas: SLX (rezago espacial de X, calculado vía **convolución Queen 3x3 sobre el
  ráster completo**, no un grafo KNN sobre la muestra — más correcto para datos de grilla
  regular) y **autologístico** (Besag 1972, análogo binario de SAR-Lag: agrega el rezago
  espacial de la propia Y como predictor).
- **Resultados (AUC en prueba, 90,000 píxeles):**
  - Probit no espacial (referencia): AUC=0.9366, McFadden ρ=0.483.
  - SLX-Probit (rezago de X): AUC=0.9409, McFadden ρ=0.500 — mejora modesta y honesta.
  - Autologístico INGENUO (rezago de Y verdadero): AUC=**1.0000** — diagnosticado
    explícitamente como **tautología, no como mejora real**: correlación entre el rezago de
    Y y Y mismo = 0.987; cuando >50% de los 8 vecinos inmediatos son Altiplano, P(el propio
    píxel también lo es)=99.78%. Los altiplanos son polígonos grandes y contiguos, así que
    conocer la etiqueta verdadera de los vecinos casi resuelve el problema por definición
    geométrica — y en un escenario real de predicción sobre área NO mapeada, esa etiqueta no
    se conocería.
  - **Autológistico CORREGIDO (dos etapas)**: en vez del rezago de Y verdadero, se usa el
    rezago espacial de la PROBABILIDAD PREDICHA por el modelo base (nunca usa ninguna
    etiqueta) — AUC=0.9384, McFadden ρ=0.488 — mejora real pero acotada sobre el modelo base,
    comparación honesta y evaluable.
  - Test de Kelejian-Prucha sobre residuos del modelo base: 433.1 (p≈0) — confirma
    dependencia espacial real, coherente con `10_SAR_altiplanos_v2.ipynb`.
- Exports: `Resultados\probabilidad_altiplano_sar_clasificacion_v2.tif`. Figuras en
  `Resultados\10_SAR_altiplanos_clasificacion_v2\` (6 PNG).

### `13_MGWR_altiplanos_clasificacion_v2.ipynb` — GWR-Binomial sobre clasificación (nuevo)
- Ejecutado de punta a punta, 32 celdas, 0 errores. N_MUESTRA=6,000 (vs. 300,000 del
  notebook SAR-clasificación) — la calibración de ancho de banda de GWR es cara (CV tipo
  leave-one-out), N=6,000 toma ~30s por ajuste, N=300,000 sería intratable.
- **Alcance reducido documentado:** se probó `MGWR` multiescala con `family=Binomial()` —
  corre sin error pero da **R²=-57** (inestabilidad numérica del backfitting con familias
  no-Gaussianas en `mgwr` 2.2.1) — se usa GWR de un solo ancho de banda en su lugar.
- **Hallazgo central (opuesto al de SAR-clasificación):** GWR generaliza PEOR que el modelo
  global simple:
  - Logística no espacial (partición aleatoria): AUC=0.9375.
  - GWR-Binomial DENTRO de su propia muestra de calibración: AUC=0.9687 (impresionante pero
    engañoso si se reportara solo).
  - GWR-Binomial FUERA de muestra (partición aleatoria, ancho de banda calibrado SOLO en
    entrenamiento): AUC=**0.5695** — cae muy por debajo del modelo base.
  - Con partición espacial por bloques de 5km (evaluación más estricta, ningún píxel de
    prueba tiene vecino inmediato en entrenamiento): logística=0.9257, GWR=**0.5357** — la
    brecha se mantiene/empeora.
  - **Diagnóstico:** no es un bug — se verificó rango/media de probabilidades predichas.
    Es sobreajuste local genuino: el ancho de banda óptimo por CV (601 vecinos de 4,200,
    14.3%) ajusta un modelo muy flexible dentro del área de calibración que no se
    transfiere bien a píxeles nuevos, a diferencia de SLX/autologístico (que agregan
    términos globales con coeficientes fijos).
- Exports: `Resultados\altiplanos_gwr_clasificacion_v2.gpkg`. Figuras en
  `Resultados\13_MGWR_altiplanos_clasificacion_v2\` (6 PNG, incluye mapas de coeficientes
  locales).

### Resumen: qué cambió (antes → después) para ambos notebooks

| | Antes (`10_SAR_v2` / `13_MGWR_v2`) | Ahora (`_clasificacion_v2`) |
|---|---|---|
| Variable respuesta | `Altitud_X` continua | `Altiplano` binaria (15.1% positivos) |
| Datos | 491 polígonos (todos Altiplano=1) | Muestra de píxeles del ráster |
| Qué medían | Relación Altitud~Pendiente+Relieve DENTRO de zonas ya sabidas como altiplano | Si el enfoque espacial mejora la PREDICCIÓN de qué es altiplano |
| SAR: resultado | SAR-Lag Pseudo R²=0.923 | Autologístico corregido: mejora real pero modesta (AUC 0.937→0.938) |
| GWR: resultado | R²=0.976 (MGWR) | GWR generaliza PEOR que el modelo global (AUC 0.937→0.570 fuera de muestra) |
| Conclusión metodológica | — | Un AUC alto dentro de la muestra de ajuste no garantiza buena generalización; SAR/SLX (términos globales) generalizaron mejor que GWR (suavizado totalmente local) para esta tarea específica |

## 4e. Plantilla cartográfica estándar aplicada a todos los mapas (2026-07-17)

**Pedido del usuario:** crear una plantilla reutilizable para todos los mapas del proyecto,
con hillshade (40% de transparencia), el borde del área de estudio, una flecha de norte y
una escala gráfica en km (franjas negras/blancas). Se probó primero sobre una sola figura
(el mapa de clusters de `01_clustering_altiplanos_v2.ipynb`) hasta que el usuario aprobó el
diseño, y luego se aplicó a **todos** los mapas geográficos de **los 12 notebooks** del
proyecto.

### `plantilla_mapas.py` (nuevo módulo, en `Codigo/`)
Funciones públicas: `agregar_hillshade`, `agregar_area_estudio`, `agregar_flecha_norte`,
`agregar_escala_grafica`, `aplicar_plantilla_mapa` (combina las 4 anteriores, se llama UNA
vez por eje antes de graficar los datos del análisis) y `posicionar_leyenda` (arma el
`legend_kwds` para que la leyenda quede junto a la flecha de norte).

**Decisiones de diseño (aprobadas por el usuario tras iterar):**
- Hillshade: `alpha=0.6` (40% de transparencia = 60% de opacidad), con **realce de
  contraste** (percentiles 2-98) porque el hillshade original es bastante claro en promedio
  (media=168/255) y se ve lavado sin este ajuste.
- Capa de datos del análisis (clusters/probabilidad/coeficientes, etc.): `alpha=0.8` (20%
  de transparencia), para que el hillshade se note un poco incluso debajo de los datos.
- Área de estudio: solo el borde (sin relleno), para no tapar nada debajo.
- Flecha de norte: esquina **superior izquierda**, anclada en **coordenadas de datos**
  (no en fracción de ejes) — necesario porque con `aspect='equal'` y un área de estudio no
  cuadrada, la fracción de ejes puede desalinearse del mapa realmente dibujado.
- Leyenda: junto a la flecha de norte, desplazada hacia el centro (`posicionar_leyenda`).
- Escala gráfica: esquina **inferior derecha**, 4 franjas negras/blancas alternadas, con
  una etiqueta numérica en cada frontera (0, y una por cada una de las 4 franjas — ej. "0",
  "25", "50", "75", "100 km").
- Para colores CONTINUOS (colorbars, no leyendas discretas): `posicionar_leyenda` NO
  aplica (un colorbar no acepta `bbox_to_anchor`/`bbox_transform`/`loc` — son kwargs de
  `Legend`, no de `Colorbar`) — se usa `legend_kwds={"shrink": ..., "label": ...}` en su
  lugar. Bug encontrado y corregido durante la aplicación a `10_SAR_altiplanos_v2.ipynb`.

**Limitación documentada:** `QStatistic.plot()` / `RectangleM.plot()` de `pointpats` no
acepta un parámetro `ax` externo (siempre crea su propia figura internamente), así que el
mapa de cuadrantes de `03_PointPattern_altiplanos_v2.ipynb`
(`04_estadistica_cuadrantes.png`) **no** se pudo componer con la plantilla — queda con su
diseño original, sin hillshade/norte/escala.

### Patrón de aplicación en cada notebook
Se agregó, en cada notebook, una celda markdown + una celda de código NUEVAS
inmediatamente después de cada celda de mapa ya existente (sin modificar la celda
original) — la celda nueva solo importa `plantilla_mapas` y vuelve a graficar la capa YA
CALCULADA, guardando el resultado en `Imágenes\<nombre_notebook>\<mismo_nombre_de_archivo>.png`
(carpeta nueva, paralela a `Resultados\`, con la misma convención de subcarpeta por
notebook).

### Notebooks actualizados (12 de 12, todos con 0 errores tras re-ejecución completa)
| Notebook | Mapas redibujados |
|---|---|
| `01_clustering_altiplanos_v2.ipynb` | `04_mapa_clusters.png` |
| `02_clustering_espacial_altiplanos_v2.ipynb` | `07_mapa_comparacion_espacial.png` (3 paneles) |
| `03_regresion_no_espacial_raster_v2.ipynb` | `03_mapa_probabilidad_altiplano.png` |
| `04_autocorrelacion_espacial_v2.ipynb` | `02_lisa_cluster_altitud_poligonos.png`, `05_lisa_residuos_raster.png` |
| `05_modelo_jerarquico_cordilleras_v2.ipynb` | `04_mapa_probabilidad_comparacion_zonas.png` (2 paneles) |
| `Clustering_Regiones_v2.ipynb` | `03_mapa_k_optimo.png`, `04_mapa_k_mayor_10.png`, `05_mapa_regiones_clustering.png`, `06_comparacion_zonas_cordillera_vs_clustering.png` (2 paneles) |
| `10_SAR_altiplanos_v2.ipynb` | `01_mapa_residuos_ols_vs_sarlag.png` (2 paneles) |
| `03_PointPattern_altiplanos_v2.ipynb` | `00_scatter_centroides.png`, `01_centrografia.png`, `02_extension_hull_alphashape.png`, `03_kde_dos_anchos_banda.png` (2 paneles), `05_observado_vs_aleatorio.png`, `08_dbscan_mapa.png` (`04_estadistica_cuadrantes.png` excluido, ver limitación arriba) |
| `13_MGWR_altiplanos_v2.ipynb` | `01_gwr_mapa_r2_local.png`, `02_gwr_mapas_coeficientes.png` (2 paneles), `03_mgwr_mapas_coeficientes.png` (2 paneles) |
| `10_SAR_altiplanos_clasificacion_v2.ipynb` | `05_mapas_probabilidad_comparacion.png` (2 paneles) |
| `13_MGWR_altiplanos_clasificacion_v2.ipynb` | `05_mapas_coeficientes_locales.png` (3 paneles) |

Todas las figuras nuevas quedan en `Imágenes\<notebook>\` (carpeta creada en esta sesión,
al mismo nivel que `Capas\`, `Raster\`, `Resultados\`, `Codigo\`). Nota: existe también una
carpeta `Imagenes\` (sin tilde) creada FUERA de esta sesión con 4 figuras antiguas de otra
iteración de trabajo — no se tocó.

## 4f. Modelo CAR con heterogeneidad espacial (2026-07-29) — `11_CAR` ya NO está pausado

**Pedido del usuario:** crear un modelo CAR que incorpore la heterogeneidad espacial (usando
los clusters de toda la zona) y evaluar sus métricas. Se implementó vía **`CARBayes` (R,
MCMC)** — INLA sigue sin correr en Windows nativo (ver sección 5). El notebook orquesta:
prep en Python → export tabla+adyacencia → `Rscript` (subprocess) → lee resultados → mapas
con la plantilla. Ejecutado de punta a punta, 30 celdas, 0 errores.

### `11_CAR_altiplanos_v2.ipynb` — CAR de Leroux binario, unidades areales de 5 km (nuevo)
- **Unidad areal = celda de 5 km** (agregación 100× desde 50 m → **2.596 celdas válidas**,
  grafo Rook totalmente conexo, 0 islas, grado medio 3,86). **No es 1 km** por restricción
  dura: `CARBayes` usa matriz de vecindad **densa** K×K y su MCMC escala ≈ **O(N²·⁵)**
  (medido: N=625→2,2 s; N=2.500→20 s; N=6.400→210 s por 1.000 muestras). A 1 km (~62.000
  celdas) la W densa sería ~30 GB, inviable.
- **Respuesta areal BINARIA** (celda = Altiplano si **≥ 25 %** de sus píxeles lo son → 558
  positivas, 21,5 %). El **binomial de conteo diverge** (τ²≈10⁶, DIC=∞): con denominadores
  hasta 10.000 cada celda se estima con precisión casi perfecta y el CAR interpola los
  logits ±∞ de las celdas 0 %/100 % en vez de suavizar. Documentado como hallazgo.
- **Prior débilmente informativo `prior.tau2 = c(2,1)` (IG(2,1), media a priori τ²=1):**
  incluso en binario, el prior vago por defecto de `CARBayes` (IG(1,0.01)) produce
  **separación perfecta** (τ²→10⁵, DIC=∞, probabilidades NaN en las 558 celdas positivas);
  la corrida corta del prototipo (2.000 muestras) lo enmascaraba, la larga (15.000) lo
  revelaba. IG(2,1) es la práctica estándar para regularizar el efecto aleatorio en outcomes
  areales binarios. Con él: τ² acotado, DIC finito, 0 NaN.
- **Tres modelos comparados** (S.glm no espacial vs S.CARleroux), cadenas 13.000 muestras /
  3.000 burn-in, ~168 s en R:

  | Modelo | DIC | WAIC | p.d | ρ (IC95%) | AUC in-sample |
  |---|---|---|---|---|---|
  | M0 · GLM no espacial (+región) | 1268,5 | 1269,0 | 5,7 | — | 0,943 |
  | **M1 · CAR Leroux (sin región)** | **658,1** | **607,5** | 303,8 | 0,993 [0,98–0,999] | ~1,0 |
  | M2 · CAR Leroux (+región) | 734,6 | 689,9 | 317,1 | 0,990 [0,97–0,999] | ~1,0 |

- **Resultados clave:**
  - El efecto espacial CAR reduce el DIC de **1268,5 → 658,1** (mejora enorme) y **ρ≈0,99**
    (dependencia espacial fortísima, casi CAR intrínseco). El mapa de φ (media posterior) es
    la heterogeneidad espacial incorporada.
  - **Hallazgo contraintuitivo (los clusters se vuelven redundantes):** agregar las 4
    regiones *encima* del CAR **empeora** el DIC (M1=658 → M2=735). El campo espacial suave
    ya reproduce la variación regional (las regiones son bloques contiguos de celdas), así
    que las dummies de región solo añaden complejidad. El CAR *subsume* a los clusters —
    distinto del modelo jerárquico (`05_v2`), donde las Regiones sí ganaban a las
    Cordilleras, porque allí no había efecto espacial que las hiciera redundantes.
  - **AUC in-sample del CAR ≈ 1 NO es capacidad predictiva:** el efecto aleatorio (~1
    parámetro por celda) reproduce el mapa observado; la comparación válida es por DIC/WAIC
    (que penalizan p.d). El GLM M0 sí da AUC honesto (0,943).
- **Arquitectura Python↔R:** el notebook escribe `celdas.csv`+`edges.csv` a
  `Resultados\11_CAR_io\`, genera `car_fit.R` desde una celda (autocontenido) y lo corre con
  `subprocess.run([RSCRIPT, ...])` fijando `R_LIBS_USER`. `RSCRIPT =
  C:\Program Files\R\R-4.6.1\bin\Rscript.exe`. Reproducible reejecutando las celdas.
- Exports: `Resultados\celdas_car_v2.gpkg` (celdas 5 km con prob/φ/clase), métricas en
  `Resultados\11_CAR_altiplanos_v2\` (2 CSV + 2 PNG: exploración, ROC). Mapas con plantilla
  en `Imágenes\11_CAR_altiplanos_v2\` (2 PNG: prob+φ, observado).

### `11_CAR_prediccion_total_v2.ipynb` — Predicción CAR a 50 m sobre toda la zona de estudio (nuevo)
- **Objetivo:** llevar el efecto espacial CAR (resolución areal de 5 km) a una predicción
  a nivel de **píxel de 50 m** sobre todo el DEM. Los notebooks `10_SAR_v2` y `13_MGWR_v2`
  modelaban *dentro* de polígonos de altiplano; este notebook extiende la predicción a
  **toda** la zona de estudio.
- **Estrategia:** rasterizar el φ del CAR M1 (mejor DIC=658,1) a 50 m con
  `rasterio.features.rasterize` (cada píxel toma el valor de su celda de 5 km, fill=0 para
  bordes = efecto neutro), y usarlo como covariable adicional en un logístico a nivel de
  píxel: `Altiplano ~ Altitud + Pendiente + Relieve + φ_CAR`.
- **Muestra de entrenamiento:** 300.000 píxeles aleatorios (SEMILLA=42).
- **Comparación de 3 modelos (evaluados sobre los ~24,8M píxeles válidos):**

  | Modelo | AUC | Pseudo R² | F1 (Altiplano) | Accuracy |
  |---|---|---|---|---|
  | Logístico base (sin CAR) | 0,9364 | 0,4829 | 0,6200 | 0,8977 |
  | **CAR-Pixel (logístico + φ)** | **0,9717** | **0,6455** | **0,7862** | **0,9371** |
  | CAR directo rasterizado (5 km) | 0,9400 | — | 0,6984 | 0,8863 |

- **Resultado clave:** el modelo **CAR-Pixel** (AUC=**0,9717**) supera a todos los modelos
  previos del proyecto: logístico no espacial (0,9522 en `03_v2`), jerárquico (0,9678 en
  `05_v2`), y SAR clasificación (AUC del `10_SAR_clasificacion_v2`). Combinar el prior
  espacial suavizado del CAR con el detalle topográfico a 50 m produce la mejor predicción.
- **Hallazgo:** el CAR directo (5 km) tiene mejor recall (0,87) pero peor precision (0,58) —
  sus predicciones son bloques gruesos que sobreclasifican. El CAR-Pixel refina esos bloques
  usando la topografía local.
- **Exports:**
  - `Resultados\prediccion_altiplano_CAR_v2.tif` — probabilidad a 50 m (modelo CAR-Pixel)
  - `Resultados\car_phi_50m_v2.tif` — efecto espacial φ rasterizado a 50 m (reutilizable)
  - Figuras en `Resultados\11_CAR_prediccion_total_v2\` (histogramas, ROC, mapas)
  - Mapas con plantilla en `Imágenes\11_CAR_prediccion_total_v2\`

### `13_MGWR_prediccion_total_v2.ipynb` — Predicción GWR-Binomial a 50 m sobre toda la zona de estudio (nuevo)
- **Objetivo:** extender el GWR-Binomial a una predicción sobre **todo** el DEM a 50 m.
  El notebook `13_MGWR_altiplanos_clasificacion_v2` demostró que el GWR sobreajusta (AUC
  fuera de muestra peor que el logístico global), pero se produce el mapa para completar
  la comparación entre modelos.
- **Estrategia:** reentrenar GWR-Binomial sobre 6.000 píxeles (limitación O(N²)) usando
  **toda** la muestra (sin partición train/test, para maximizar la cobertura de coeficientes),
  extraer las 4 superficies de coeficientes (intercepto + 3 predictores), interpolarlas al
  grid completo vía `LinearNDInterpolator` (con fallback `NearestNDInterpolator` fuera del
  convex hull), y aplicar la función logit.
- **GWR-Binomial:** ancho de banda óptimo (AICc) = **504 m**, AICc=2000,4, parámetros
  efectivos=96,7.
- **Comparación (evaluada sobre ~24,8M píxeles válidos):**

  | Modelo | AUC | F1 (Altiplano) | Accuracy |
  |---|---|---|---|
  | **GWR-Binomial (interpolado)** | **0,9620** | **0,7425** | **0,9271** |
  | Logístico global (referencia) | 0,9364 | 0,6197 | 0,8977 |

- **Nota de cautela:** el AUC=0,9620 del GWR es in-sample (coeficientes extraídos de la
  muestra de entrenamiento e interpolados). La evaluación honesta en
  `13_MGWR_altiplanos_clasificacion_v2` mostró que el GWR sobreajusta en partición por
  bloques espaciales (AUC out-of-sample peor que el logístico global). Este mapa tiene
  valor exploratorio pero no debe tomarse como evidencia de superioridad predictiva.
- **Exports:**
  - `Resultados\prediccion_altiplano_GWR_v2.tif` — probabilidad a 50 m
  - `Resultados\coeficientes_gwr_50m_v2.tif` — 4 bandas (Intercepto/Altitud/Pendiente/Relieve)
  - Figuras en `Resultados\13_MGWR_prediccion_total_v2\` (histogramas, ROC, coeficientes, mapas)
  - Mapas con plantilla en `Imágenes\13_MGWR_prediccion_total_v2\`

## 4g. Procesos Gaussianos y Kriging sobre malla de 3 km (2026-07-30)

Datos base: **malla cuadrada de 3 km** (`Capas\Malla_3km.shp`, 6,902 puntos, EPSG:32618)
con buffers (`Capas\Malla_3km_Buffer.shp`) conteniendo estadísticas zonales de 8 variables
topográficas (Altitud, Relieve, Pendiente, Amax500, Amax100, Amin100, DifA10_100, SlpD10_50)
más la variable binaria Altiplano. Prevalencia de Altiplano=1: **15.1%** (1,042 de 6,902).

### `14_GP_altiplanos_v2.ipynb` — Procesos Gaussianos para clasificación (nuevo)

- **3 modelos comparados**, todos con split 70/30 estratificado (SEMILLA=42):
  1. **Logística** (4,831 train): AUC=**0.9613**, Accuracy=0.9189
  2. **GP Covariables** (2,500 subsample, kernel RBF ARD con 8 features): AUC=**0.9729**
  3. **GP Covariables+Spatial** (2,500 subsample, RBF ARD con 8 features + X,Y): AUC=**0.9731**
- GP subsampled a **N_GP=2,500** puntos para evitar timeout (O(N³) de la aproximación de
  Laplace). Tiempo: ~22 min por modelo GP.
- **Análisis de lengthscales** del kernel ARD (GP Cov): variables más relevantes por escala
  corta = **Altitud** (ls=0.96) y **Amax100** (ls=1.69); variable irrelevante =
  **DifA10_100** (ls=100). Coordenadas XY en GP Spatial con ls muy largos (X=34.4, Y=100),
  confirmando que las covariables ya capturan la estructura espacial.
- **Hallazgo clave:** agregar coordenadas espaciales al GP apenas mejora el AUC (0.9729 →
  0.9731) — la información topográfica es suficiente.
- **Matriz de confusión y ROC con clase positiva explícita (2026-07-31):** se agregó
  verificación explícita de `classes_` con `assert` de que `predict_proba[:, 1]` = P(Altiplano=1)
  y `pos_label=1` en `roc_curve` (nunca asumir la orientación — convención del proyecto).
  Confirmado: la ROC/AUC ya estaba respecto a Altiplano=1 (AUC~0.97, no invertido). Nueva
  figura dedicada de matrices de confusión (`ConfusionMatrixDisplay`) para los 3 modelos con
  etiquetas No Altiplano/Altiplano. Confusión (test, VN/FP/FN/VP): Logística 1700/58/110/203,
  GP Cov 1709/49/71/242, GP Esp 1707/51/70/243. GP reduce falsos negativos de 110 a ~70
  (mejor Recall de Altiplano: 0.649 → 0.773).
- **Plantilla cartográfica aplicada (2026-07-31):** se agregaron celdas con hillshade, norte,
  escala y borde del área de estudio a: (1) mapa de puntos Altiplano (rojo) vs No Altiplano
  (negro), y (2) panel 2×3 de mapas de predicción e incertidumbre. Figuras con plantilla en
  `Imágenes\14_GP_altiplanos_v2\`.
- **Exports:** `Resultados\gp_clasificacion_v2.gpkg` (prob_log, prob_gp1, prob_gp2, ent_gp1,
  ent_gp2, pred_gp2, split), figuras en `Resultados\14_GP_altiplanos_v2\`
  (`00_mapa_puntos_altiplano.png`, `01_mapas_prediccion_incertidumbre.png`,
  `02_curvas_roc.png`, `03_matrices_confusion.png`), figuras con plantilla en
  `Imágenes\14_GP_altiplanos_v2\` (`00_mapa_puntos_altiplano.png`,
  `01_mapas_prediccion_incertidumbre.png`).

### `16_GP_regresion_espacial_v2.ipynb` — GP Regresión con verosimilitud Gaussiana (nuevo)

- **Objetivo:** replicar el enfoque del **Capítulo 16 del libro guía** (INLA-SPDE en R para
  variables continuas) adaptado a Python con `GaussianProcessRegressor` de scikit-learn.
  A diferencia del NB14 (GP clasificación, verosimilitud Bernoulli), aquí se trata Altiplano
  0/1 como variable continua (verosimilitud gaussiana) y se calculan **probabilidades de
  excedencia** P(ŷ > 0.5) usando la CDF gaussiana exacta — análogo directo al INLA del libro.
- **2 modelos GP comparados** más logística de referencia, split 70/30 estratificado (SEMILLA=42),
  **N_GP=1,500** puntos (reducido vs. NB14 para caber en el timeout de 1800 s):
  1. **Logística** (referencia): AUC=**0.9613**, Acc=0.9189, F1=0.7073
  2. **GP Reg. Covariables** (RBF ARD × 8 features, 163 s): AUC=**0.9683**, Acc=0.9396, F1=0.7856
  3. **GP Reg. Cov+Espacial** (RBF ARD × 10 features incluyendo X/Y, 332 s): AUC=**0.9726**, Acc=0.9416, F1=0.7946
- **Métricas de regresión** (novedad respecto al NB14): MSE=0.0479 / R²=0.626 para GP Cov;
  MSE=0.0456 / R²=0.645 para GP Cov+Esp. El R² modesto (predicción continua de datos 0/1)
  confirma la limitación teórica de usar verosimilitud gaussiana en datos binarios.
- **Predicciones fuera de [0,1]:** GP Cov produce 639 valores negativos y 32 mayores a 1 en
  2,071 puntos de prueba — requiere clip a [0,1], inherente al modelo gaussiano sobre datos discretos.
- **Lengthscales ARD kernel (GP Cov):** variables más relevantes = **Altitud** (ls=0.972),
  **Amax100** (ls=1.03), **Relieve** (ls=0.764). Variables irrelevantes = **DifA10_100** (ls=100),
  **SlpD10_50** (ls=100). Coherente con el NB14.
- **GP Cov+Espacial:** las coordenadas X/Y tienen lengthscales muy altos (X=0.832, Y=100 —
  ambiguo), confirmando que las covariables topográficas ya capturan la mayor parte de la
  estructura espacial (igual conclusión que NB14 y NB15).
- **Probabilidades de excedencia P(ŷ > 0.5):** calculadas con `scipy.stats.norm.cdf` sobre
  la distribución predictiva exacta (μ*, σ*) — ventaja clave de la regresión GP sobre
  clasificación GP (que requeriría integración numérica).
- **Comparación con NB14 (GP Clasificación):**

  | Modelo | Tipo GP | AUC | F1 | Recall | Tiempo |
  |---|---|---|---|---|---|
  | Logística | — | 0.9613 | 0.7073 | 0.649 | 0 s |
  | **GP Reg. Cov** | Regresión | **0.9683** | **0.7856** | 0.732 | 163 s |
  | **GP Reg. Cov+Esp** | Regresión | **0.9726** | **0.7946** | 0.748 | 332 s |
  | GP Clasif. Cov (NB14) | Clasificación | 0.9729 | 0.8013 | 0.773 | 864 s |
  | GP Clasif. Cov+Esp (NB14) | Clasificación | 0.9731 | 0.8007 | 0.776 | 997 s |

  GP Regresión alcanza AUC muy similar al GP Clasificación en **⅓ del tiempo** (332 s vs 864-997 s),
  con recall de Altiplano ligeramente menor (0.748 vs 0.773). Para datos binarios con desbalance
  85/15, el GP Clasificación (Bernoulli) es teóricamente correcto; el GP Regresión es un atajo
  práctico con penalización pequeña en recall.
- **Bug técnico resuelto:** primer intento con N_GP=2,500 y n_restarts_optimizer=2 superó el
  timeout de 600 s de nbconvert. Segundo intento (N_GP=1,500, n_restarts=1, timeout=1800 s) falló
  en la celda de mapas con plantilla (9 subplots en una figura). Solución final: (1) caché pickle
  de los modelos GP, (2) mapas con plantilla divididos en 3 figuras individuales. Modelos cacheados
  en `Resultados\16_GP_regresion_espacial_v2\_cache\` (18 MB c/u).
- **Exports:**
  - `Resultados\gp_regresion_espacial_v2.gpkg` (score_cov, score_sp, prob_cov, prob_sp,
    std_cov, std_sp, pexc_cov, pexc_sp, pred_sp, split) — 6,902 registros
  - Figuras en `Resultados\16_GP_regresion_espacial_v2\`:
    `00_mapa_puntos_altiplano.png`, `01_mapas_prediccion_incertidumbre_excedencia.png`,
    `02_mapa_plantilla_0.png` (score), `02_mapa_plantilla_1.png` (incertidumbre),
    `02_mapa_plantilla_2.png` (excedencia), `02_curvas_roc.png`, `03_matrices_confusion.png`
  - Figuras con plantilla también en `Imágenes\16_GP_regresion_espacial_v2\`

### `15_Kriging_altiplanos_v2.ipynb` — Semivariograma y Kriging Ordinario (nuevo)

- **Semivariograma empírico** calculado sobre variable Altiplano directa y sobre residuos
  logísticos, con submuestra de 3,000 puntos y 30 bins.
- **Ajuste de 3 modelos teóricos** al variograma de residuos:
  - Exponencial (mejor): R²=**0.8118**, nugget=0.0519, sill parcial=0.0139, rango=58.7 km
  - Esférico: R²=0.7907
  - Gaussiano: R²=0.7370
- **Ratio nugget/sill total = 0.79** — el 79% de la variación residual es ruido (nugget),
  solo 21% es estructura espacial aprovechable.
- **Kriging Ordinario** de los residuos logísticos (pykrige, auto-fit del variograma):
  - Pykrige ajustó range=159 m (menor que el espaciado de 3 km de la malla), confirmando
    la ausencia de estructura espacial residual a esta escala.
  - Corrección por kriging prácticamente nula: residuos krigeados constantes (~-0.0035).
- **Resultados finales (test):**
  - Logística: AUC=**0.9613**, Acc=0.9189, F1=0.7073, Pseudo R²=0.581
  - Logística + Kriging: AUC=**0.9613**, Acc=0.9194, F1=0.7086, Pseudo R²=0.583
- **Conclusión:** las covariables topográficas ya capturan la estructura espacial de los
  altiplanos — kriging de residuos no mejora la predicción. Resultado coherente con el GP
  (notebook 14), donde las coordenadas XY tampoco aportaron.
- **Bug corregido:** versión inicial usaba parametrización manual del variograma con
  discrepancia de convención en el rango (pykrige usa rango práctico = 3×a), produciendo
  residuos krigeados extremos [-33, 39] y AUC=0.49. Corregido dejando que pykrige auto-ajuste.
- **Plantilla cartográfica aplicada (2026-07-31):** se agregaron celdas con hillshade, norte,
  escala y borde del área de estudio a: (1) nuevo mapa de puntos Altiplano (rojo) vs No
  Altiplano (negro), y (2) panel 2×3 de mapas de predicción/kriging. Figuras con plantilla en
  `Imágenes\15_Kriging_altiplanos_v2\`.
- **Exports:** `Resultados\kriging_clasificacion_v2.gpkg` (prob_log, res_krig, prob_krig,
  std_krig, pred_krig, split), figuras en `Resultados\15_Kriging_altiplanos_v2\`
  (`00_mapa_puntos_altiplano.png`, `01-05_*.png`), figuras con plantilla en
  `Imágenes\15_Kriging_altiplanos_v2\` (`00_mapa_puntos_altiplano.png`,
  `05_mapas_kriging.png`).

## 4h. Modelos Autorregresivos Areales y CAR/INLA — Sección 3 completa (2026-08-04)

Implementación de **todos los modelos de la Sección 3 del libro guía** (Áreas) sobre
**celdas de 5 km** (2,596 celdas, adyacencia Rook, mismos datos que `11_CAR_altiplanos_v2`).
Covariables: altitud, pendiente, relieve (estandarizadas) + 3 dummies de región (4 zonas del
clustering, drop_first=True, referencia=Región 0 C. Central-Magdalena).

### `09_autorregresivos_areales_v2.ipynb` — 8 modelos autorregresivos (nuevo)
- Ejecutado de punta a punta, 42 celdas, 0 errores.
- **Enfoque LPM** (Modelo de Probabilidad Lineal): la variable binaria Altiplano se trata
  como continua para usar los estimadores ML/GMM de `spreg`. Predicciones recortadas a [0,1].
- **Variables con rezago espacial (SLX/SDM/SDEM/GNS):** solo las topográficas (W_altitud_s,
  W_pendiente_s, W_relieve_s). Las dummies de región NO se rezagan (indicadores fijos de zona,
  no gradientes continuos).
- **Resultados (8 modelos, in-sample sobre 2,596 celdas):**

  | Modelo | Estimador | AUC | Accuracy | F1 | AIC |
  |---|---|---|---|---|---|
  | OLS | OLS | 0.9231 | 0.8656 | 0.6039 | 1523.4 |
  | SLX | OLS+WX | 0.9238 | 0.8679 | 0.6116 | 1515.5 |
  | **SAR** | ML_Lag | **0.9617** | 0.9114 | 0.7727 | 749.4 |
  | SEM | ML_Error | 0.9172 | 0.8586 | 0.5677 | 703.9 |
  | **SDM (Durbin)** | ML_Lag+WX | **0.9673** | **0.9183** | **0.7926** | 704.3 |
  | SDEM | ML_Error+WX | 0.9216 | 0.8636 | 0.5903 | 701.6 |
  | SAC (SARAR) | GM_Combo_Het | 0.9489 | 0.8979 | 0.7160 | — |
  | GNS | GM_Combo_Het+WX | 0.8763 | 0.8139 | 0.2581 | — |

- **Mejor por AUC: SDM (Durbin)** — AUC=0.9673, combina lag de Y (ρ) + lag de X topográficas.
- **Mejor por AIC: SDEM** — AIC=701.6 (más parsimonioso que SDM con AIC=704.3).
- **Hallazgo:** el rezago de la variable respuesta (ρWy en SAR/SDM) mejora sustancialmente
  la predicción (AUC ~0.96-0.97) vs. modelos sin lag de Y (OLS/SLX/SEM/SDEM ~0.91-0.92).
  GNS (el modelo más general) tiene el peor AUC — sobreparametrizado con GMM.
- **Exports:** `Resultados\autorregresivos_areales_v2.gpkg` (prob de cada modelo + pred_best),
  métricas en `Resultados\09_autorregresivos_areales_v2\metricas_autorregresivos.csv`.
  Figuras: histogramas, mapa observado, curvas ROC, matrices de confusión, mapas de predicción
  (grilla 3×3), mapa con plantilla del mejor modelo.

### `11_CAR_INLA_comparacion_v2.ipynb` — ICAR, BYM (INLA) + Leroux (CARBayes) (nuevo)
- Ejecutado de punta a punta, 28 celdas, 0 errores. Pipeline Python→R→Python.
- **4 modelos ajustados** (GLM no espacial como referencia + 3 CAR):
  - **INLA:** ICAR (`model="besag"`, scale.model=TRUE), BYM (`besag`+`iid`).
    Priors por defecto (PC priors para precisión). `control.compute = list(dic=TRUE, waic=TRUE)`.
  - **CARBayes:** Leroux (`S.CARleroux`), `trials=rep(1,N)` para familia binomial,
    `prior.tau2=c(2,1)` (IG(2,1) para evitar separación), 13,000 muestras MCMC / 3,000 burn-in.

  | Modelo | Motor | DIC | WAIC | AUC | Accuracy | F1 |
  |---|---|---|---|---|---|---|
  | GLM (no espacial) | INLA | 1270.3 | 1271.1 | 0.9427 | 0.8983 | 0.7505 |
  | ICAR | INLA | 1340.5 | 2348.6 | 0.9953 | 0.9761 | 0.9443 |
  | BYM | INLA | 1188.0 | 1292.9 | 0.9953 | 0.9773 | 0.9469 |
  | **Leroux** | CARBayes | **701.4** | **674.9** | **0.9999** | **0.9958** | **0.9901** |

- **Mejor por DIC/WAIC/AUC: Leroux** — DIC=701.4, AUC=0.9999 (separación casi perfecta
  in-sample, ~1 parámetro por celda).
- **Hiperparámetros:** ICAR τ=0.106, BYM τ_besag=0.106 / τ_iid=22054 (componente iid
  irrelevante), Leroux ρ≈0.99 (dependencia espacial casi intrínseca).
- **Comparación con NB09 (tabla combinada de 12 modelos):** los modelos CAR (ICAR/BYM/Leroux)
  superan a todos los autorregresivos en AUC. Leroux (AUC=0.9999) >> SDM (0.9673) >> SAR
  (0.9617). Sin embargo, el AUC del CAR es in-sample con efecto aleatorio — la comparación
  válida es por DIC/WAIC.
- **Bug corregido:** `S.CARleroux` requiere `trials=rep(1,N)` para `family="binomial"`;
  sin él lanza "trials argument not specified". También `posicionar_leyenda()` de
  `plantilla_mapas.py` lanza TypeError en colorbars (solo funciona para leyendas
  categóricas) — se reemplazó por colorbar manual con `ScalarMappable` para mapas de
  probabilidad continua.
- **Exports:** `Resultados\car_inla_comparacion_v2.gpkg` (prob de 4 modelos + efectos
  espaciales φ), CSVs en `Resultados\11_CAR_INLA_io\`. Figuras en
  `Resultados\11_CAR_INLA_comparacion_v2\` y `Imágenes\11_CAR_INLA_comparacion_v2\`.

## 4i. Evaluación de la Sección 3 a 50 m — `09b_prediccion_seccion3_50m_v2.ipynb` (2026-08-04)

Notebook que **lleva los 12 modelos areales** (8 autorregresivos + 4 CAR/INLA) a resolución
de **50 m** sobre la zona de estudio completa (~24,8M píxeles válidos), evaluándolos contra
el raster real de Altiplanos. Usa la estrategia de **pixel-enhancement** de
`11_CAR_prediccion_total_v2`: rasterizar el efecto areal (probabilidad o φ) a 50 m y usarlo
como covariable adicional en un logístico a nivel de píxel.

- **Estrategia:** `Altiplano ~ Altitud + Pendiente + Relieve + Efecto_areal` (logístico,
  muestra=300k, SEMILLA=42). Para ICAR/BYM/Leroux se usa el efecto espacial φ (no la prob);
  para los demás se usa la probabilidad rasterizada.
- **Datos:** 24,783,966 píxeles válidos (15.1% Altiplano=1), grilla 8276×6084.
- Ejecutado de punta a punta, 24 celdas, 0 errores. Tiempo total: 21.5 min.

**Resultados pixel-enhanced (50 m) — ranking por AUC:**

| Modelo | AUC | Accuracy | F1 | Precision | Recall | Pseudo R² |
|---|---|---|---|---|---|---|
| **Leroux** | **0.9729** | 0.9382 | 0.7906 | 0.8107 | 0.7716 | 0.6528 |
| ICAR | 0.9683 | 0.9330 | 0.7711 | 0.7975 | 0.7464 | 0.6249 |
| BYM | 0.9681 | 0.9328 | 0.7702 | 0.7970 | 0.7452 | 0.6237 |
| SDM (Durbin) | 0.9626 | 0.9253 | 0.7391 | 0.7857 | 0.6977 | 0.6000 |
| SAR | 0.9611 | 0.9237 | 0.7324 | 0.7822 | 0.6885 | 0.5924 |
| GNS | 0.9603 | 0.9254 | 0.7378 | 0.7902 | 0.6919 | 0.5892 |
| SAC (SARAR) | 0.9534 | 0.9162 | 0.7020 | 0.7615 | 0.6511 | 0.5565 |
| GLM (INLA) | 0.9531 | 0.9161 | 0.7044 | 0.7567 | 0.6589 | 0.5546 |
| SLX | 0.9470 | 0.9084 | 0.6688 | 0.7400 | 0.6101 | 0.5265 |
| OLS | 0.9466 | 0.9081 | 0.6675 | 0.7393 | 0.6085 | 0.5245 |
| SDEM | 0.9462 | 0.9075 | 0.6652 | 0.7375 | 0.6058 | 0.5228 |
| SEM | 0.9455 | 0.9067 | 0.6617 | 0.7354 | 0.6014 | 0.5193 |
| Logístico base | 0.9364 | 0.8977 | 0.6200 | 0.7073 | 0.5518 | 0.4829 |

- **Mejor modelo: Leroux-Pixel** (AUC=0.9729), seguido de ICAR/BYM (~0.968).
  El Leroux-Pixel AUC=0.9729 coincide prácticamente con el CAR-Pixel de
  `11_CAR_prediccion_total_v2` (AUC=0.9717), confirmando la robustez del enfoque.
- **Mejora del pixel-enhancement vs directo:** todos los modelos mejoran al pasar de la
  rasterización directa al pixel-enhanced. Mejora promedio: +0.05 AUC. Mayor mejora: GNS
  (+0.1228, de 0.8375 a 0.9603). Menor: Leroux (+0.0330, ya partía de 0.9400).
- **Hallazgo clave:** los modelos autorregresivos con lag de Y (SAR, SDM, GNS) mejoran más
  que los de error espacial (SEM, SDEM) al pasar a 50 m. Los modelos CAR (ICAR/BYM/Leroux)
  siguen dominando gracias a su efecto espacial φ más rico.
- **Exports:**
  - `Resultados\prediccion_seccion3_mejor_50m_v2.tif` — GeoTIFF del mejor modelo (Leroux-Pixel)
  - `Resultados\prediccion_seccion3_todos_50m_v2.tif` — GeoTIFF multibanda (12 bandas)
  - `Resultados\09b_prediccion_seccion3_50m_v2\metricas_seccion3_50m.csv` — métricas completas
  - Figuras: histogramas, curvas ROC, comparación directo vs pixel, mapas con plantilla

## 5. Entorno R instalado en esta sesión (2026-07-17)

- **R 4.6.1** instalado vía `winget install RProject.R` en `C:\Program Files\R\R-4.6.1\`.
- **Rtools 4.5** instalado vía `winget install RProject.Rtools` en `C:\rtools45\` (necesario
  para que ciertos paquetes con post-instalación tipo Unix funcionen correctamente en
  Windows).
- **Librería de paquetes de usuario:** `C:\Users\MSI\AppData\Local\R\win-library\4.6\`
  (la librería por defecto bajo `Program Files` no es escribible sin permisos de administrador).
- **Paquetes CRAN instalados y verificados (`requireNamespace` OK):** `sf`, `dplyr`, `spdep`,
  `spatialreg` (requería `multcomp`, instalado aparte), `CARBayes`, `CARBayesdata`, `mgcv`,
  `viridis`, `ggplot2`, `ggspatial`, `cowplot`, `broom`, `sjPlot`, `pROC`, `MuMIn`, `pscl`,
  `lme4`, `multcomp`.
- **INLA 26.6.8** — instalada exitosamente desde el repo testing:
  `install.packages('INLA', repos=c(CRAN='https://cloud.r-project.org', INLA='https://inla.r-inla-download.org/R/testing'), dep=TRUE)`.
  Versión anterior fallaba por falta de binarios Windows; el repo testing los tiene.
  Los modelos CAR (`11_CAR`) usan `CARBayes` (no INLA), por lo que no se vieron afectados.

## 4. Pendiente / próximos pasos

- **TODOS los métodos del libro guía están completados**, incluido `11_CAR`
  (`11_CAR_altiplanos_v2.ipynb`, vía CARBayes — ver sección 4f). Ya no queda ningún método
  pendiente de implementar.
- **TODOS los modelos producen predicción a 50 m sobre toda la zona de estudio** — resuelto
  con los notebooks `11_CAR_prediccion_total_v2.ipynb`, `13_MGWR_prediccion_total_v2.ipynb`, y
  `09b_prediccion_seccion3_50m_v2.ipynb` (12 modelos areales de la Sección 3 evaluados a 50 m).
- Reajustar el modelo jerárquico (`05_modelo_jerarquico_cordilleras_v2.ipynb`) usando la
  nueva zonificación de `Clustering_Regiones_v2.ipynb` en vez de las 3 Cordilleras, y
  comparar métricas — **ya resuelto** en la corrección de la sección 4b (Regiones supera a
  Cordilleras en todas las métricas).
- **Ranking de modelos por AUC (actualizado con evaluación a 50 m de Sección 3):**

  | Modelo | Notebook | AUC | Datos | Nota |
  |---|---|---|---|---|
  | **GP Clasif. Cov+Spatial** | `14_GP_altiplanos_v2` | **0,9731** | Malla 3 km (test) | |
  | **Leroux-Pixel** | `09b_prediccion_seccion3_50m_v2` | **0,9729** | **Raster 50 m** | pixel-enhanced |
  | GP Clasif. Covariables | `14_GP_altiplanos_v2` | 0,9729 | Malla 3 km (test) | |
  | **GP Reg. Cov+Espacial** | `16_GP_regresion_espacial_v2` | **0,9726** | Malla 3 km (test) | |
  | CAR-Pixel (logístico + φ) | `11_CAR_prediccion_total_v2` | 0,9717 | Raster 50 m | |
  | GP Reg. Covariables | `16_GP_regresion_espacial_v2` | 0,9683 | Malla 3 km (test) | |
  | ICAR-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9683 | Raster 50 m | pixel-enhanced |
  | BYM-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9681 | Raster 50 m | pixel-enhanced |
  | Jerárquico (Regiones) | `05_modelo_jerarquico_cordilleras_v2` | 0,9678 | Raster 50 m | |
  | SDM (Durbin)-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9626 | Raster 50 m | pixel-enhanced |
  | GWR-Binomial (interpolado)* | `13_MGWR_prediccion_total_v2` | 0,9620 | Raster 50 m | |
  | SAR-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9611 | Raster 50 m | pixel-enhanced |
  | GNS-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9603 | Raster 50 m | pixel-enhanced |
  | Logístico (malla) | `14_GP_altiplanos_v2` / `15_Kriging` / `16_GP_Reg` | 0,9613 | Malla 3 km (test) | |
  | SAC-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9534 | Raster 50 m | pixel-enhanced |
  | GLM (INLA)-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9531 | Raster 50 m | pixel-enhanced |
  | Logístico no espacial | `03_regresion_no_espacial_raster_v2` | 0,9522 | Raster 50 m | |
  | SLX-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9470 | Raster 50 m | pixel-enhanced |
  | OLS-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9466 | Raster 50 m | pixel-enhanced |
  | SDEM-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9462 | Raster 50 m | pixel-enhanced |
  | SEM-Pixel | `09b_prediccion_seccion3_50m_v2` | 0,9455 | Raster 50 m | pixel-enhanced |
  | Logístico base (sin efecto) | `09b_prediccion_seccion3_50m_v2` | 0,9364 | Raster 50 m | referencia |

  *\*AUC in-sample; evaluación out-of-sample peor que logístico global (sobreajuste documentado).*
  Nota: GP y Kriging usan malla de 3 km (6,902 puntos); los modelos pixel-enhanced de la
  Sección 3 (`09b`) se evalúan sobre el raster de 50 m (~24,8M píxeles). Los modelos areales
  originales (NB09/NB11, celdas 5 km in-sample con AUC 0.91–0.9999) ya **no aparecen** en el
  ranking — la evaluación comparable es su versión pixel-enhanced a 50 m.
  GP Regresión (NB16) alcanza AUC prácticamente igual al GP Clasificación (NB14) en ⅓ del tiempo
  (332 s vs 864-997 s), con ligera penalización en recall (0.748 vs 0.773).
