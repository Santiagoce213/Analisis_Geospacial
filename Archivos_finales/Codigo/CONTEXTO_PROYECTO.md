# Contexto del proyecto — Análisis Geoespacial: Altiplanos

> Documento de contexto para continuar esta conversación con Claude en sesiones futuras.
> Última actualización: 2026-07-16.

## 1. Contexto del curso y del trabajo

- Curso de posgrado **Análisis Geoespacial** (Prof. Edier Aristizábal). Trabajo individual
  evaluado en 3 entregas (todas vía GitHub): 2.1 Problema (10%), **2.2 Avances (30%,
  actual)**, 2.3 Final (30%) + escrito tipo artículo (30%).
- La 2.2 se entrega "luego de terminar el módulo de datos discretos" → alcance = **Partes
  I-III del libro** (Intro, Puntos, Áreas). **Parte IV (Superficies/Kriging) está fuera de
  alcance.**
- Libro base: `https://edieraristizabal.github.io/Libro_AnalisisGeoespacial/` (se analizaron
  a fondo, código a código, los notebooks de las Partes I-III descargados directamente del
  repo de GitHub `edieraristizabal/Libro_AnalisisGeoespacial`).
- Tema del trabajo: **altiplanos** en los Andes colombianos. El usuario **ya delimitó a mano
  491 polígonos de altiplano** (no contiguos entre sí — no comparten borde), usando criterios
  de relieve relativo, pendiente y altitud.

## 2. Datos disponibles

### 2.1a Capa de zonas geográficas (3 cordilleras)
- `Capas\Cordilleras.shp` — 3 polígonos, campo `Id`: **1=Cordillera Occidental**,
  **2=Cordillera Central**, **3=Serranía de San Lucas**. CRS EPSG:32618. Cubre el 100% del
  área válida del DEM (0 píxeles quedan sin zona). Usada en `05_modelo_jerarquico_cordilleras.ipynb`.

### 2.1 Capa de polígonos (491 altiplanos)
- `Capas\Estadisticas_Cluster.shp` — shapefile original con estadísticas zonales por
  polígono: `Altitud_X/St`, `Alt_90/50/10`, `Relieve_X/St`, `Rel_90/50/10`, `Pend_X/St`,
  `Slp_90/50/10`, `Área`, `Geo_Value`, `Geología` (7 categorías: I. Plutónica, I. Volcánica,
  M. Alto/Medio grado, S. Gruesos/Medio/Fino), coordenadas de centroide (`Latitud`,
  `Longitud` ± Max/Min). CRS: EPSG:32618. 426 Polygon + 65 MultiPolygon.
- `Capas\Clusters.shp` — mismos 491 polígonos (mismo `.shp`, mismo tamaño de archivo),
  usado para superponer bordes sobre mapas ráster.
- **Bug de encoding conocido:** pyogrio/GDAL no aplica el encoding UTF-8 del `.cpg` a los
  **nombres de columna** del `.dbf` (sí a los valores), por lo que `Geología`/`Área` llegan
  corruptos al leer el `.shp` directamente. Solución usada: leer los nombres reales del
  encabezado binario del `.dbf` (función `nombres_reales_columnas_dbf` presente en los
  scripts 01 y 02). **Los GeoPackage (`.gpkg`) NO tienen este problema** — se pueden leer
  directamente sin el workaround.

### 2.2 Capas ráster (carpeta `Raster\50m_UTM\Analisis\`)
Todas en EPSG:32618, 50 m de resolución, grilla de referencia = DEM: **6084 x 8276 píxeles**,
transform con esquina superior izquierda en (313611.67, 978277.15).

| Capa (nombre en análisis) | Archivo |
|---|---|
| **Altitud** (grilla de referencia) | `DEM_NA_50.tif` |
| **Pendiente** | `Slp_NA_50.tif` |
| Relieve (ventanas 3/5/10) | `Rel_NA_3/5/10.tif` |
| Residuo vs. media (ventanas 5/10) | `Resta_Alt_NA_Alt_mean_5/10.tif` |
| Residuo vs. mínimo (ventanas 3/10/50/100) | `Resta_Alt_NA_Alt_min_X.tif` |
| Residuo vs. máximo (ventanas 3/10/50/100) | `Resta_Alt_max_X_Alt_NA.tif` |
| Diferencia de medias (3-10, 5-10) | `Resta_Alt_mean_3_10.tif`, `_5_10.tif` |
| Pendiente de residuo-de-media (5/10) | `Slp_Resta_Alt_NA_Alt_mean_5/10.tif` |
| Pendiente de diferencia-de-medias (3-10, 5-10) | `Slp_Resta_Alt_mean_3_10/5_10.tif` |
| **Variable respuesta**: `Altiplanos.tif` (1 = altiplano) | ⚠️ grilla **distinta** (5856x7601), desalineada ~0.98 píxeles respecto al DEM. Requiere realinearse con `rasterio.warp.reproject` (nearest neighbor) antes de usarse. |

- Total píxeles: 50,351,184. Válidos según DEM: 24,814,468 (49.3%). Válidos combinando
  TODAS las capas (algunas ventanas grandes tienen NoData en bordes más anchos que el DEM):
  **24,783,966** (49.2%). De estos, Altiplano=1: 3,746,338 (15.1%) — desbalance de clases.
- Se exportó el resultado de la regresión como `Resultados\probabilidad_altiplano.tif`.

## 3. Entorno técnico

- Python: **NO hay python en PATH**. Usar Anaconda: `C:\Users\MSI\anaconda3\python.exe`.
- Paquetes instalados durante esta conversación (no venían por defecto):
  `esda`, `splot`, `spreg` (ecosistema PySAL para autocorrelación espacial). `tslearn` y
  `statsmodels` ya estaban disponibles.
- **`esda.Moran` NO acepta parámetro `seed`** (a diferencia de `esda.Moran_Local`, que sí).
  Para reproducibilidad, usar `np.random.seed(SEMILLA)` antes de llamar a `esda.Moran(...)`.
- **`pd.get_dummies(..., drop_first=True)`** descarta la categoría **alfabéticamente
  primera**, no necesariamente la que uno espera como "referencia". Si se necesita una
  categoría de referencia específica, forzar el orden con
  `pd.Categorical(serie, categories=[...])` antes de `get_dummies`.
- Modelo jerárquico bayesiano (intercepto aleatorio) disponible en
  `statsmodels.genmod.bayes_mixed_glm.BinomialBayesMixedGLM` (variational Bayes). Con
  ~100,000 filas y 18 predictores tarda ~40-100s en ajustar (`fit_vb()`).
- Consola PowerShell no muestra tildes correctamente (problema de codepage, no de los
  datos) — para verificar encoding, escribir a archivo UTF-8 y leer con la tool `Read`, o
  usar `repr()`.
- SEMILLA usada en todo el proyecto: **42** (garantiza reproducibilidad entre scripts).

## 4. Trabajo realizado — resumen por archivo

Todos los scripts/notebooks están en `Codigo\`. Los `.py` usan celdas `# %%` (compatibles
con VS Code Interactive). Los `.ipynb` se ejecutaron de punta a punta con
`jupyter nbconvert --execute` y no tienen errores.

### `01_clustering_altiplanos.py` — Clustering NO espacial de los 491 altiplanos
- Variables usadas (9, estandarizadas): `Altitud_X`, `Altitud_St`, `Alt_90`, `Alt_50`,
  `Alt_10`, `Relieve_X`, `Relieve_St`, `Pend_X`, `Pend_St`. **Área y Geología excluidas**
  (Área = tamaño del polígono, no morfometría; Geología = categórica).
- Métodos: K-means y Ward jerárquico, comparados con **Silhouette (SS) y
  Calinski-Harabasz (CH)** para k=2 a 50. Ambos criterios coinciden: **k=2 es
  consistentemente el óptimo global** (SS=0.401, CH=269.3), decreciendo con k.
- Comparación adicional con **TimeSeriesKMeans (DTW)**: K-means euclidiano supera a DTW en
  todos los k comparados — valida el enfoque euclidiano simple.
- `K_ELEGIDO = 4` quedó como valor demostrativo/ajustable en el script (no es el óptimo
  puro por SS, pero da una tipología más granular con sentido geomorfológico).
- Salidas: correlación de variables, gráfico de codo/SS/CH (3 paneles), dendrograma, mapa
  de clusters, heatmap de perfil por cluster, comparación DTW vs. K-means.
- Export: `Resultados\altiplanos_clasificados.gpkg`.

### `02_clustering_espacial_altiplanos.py` — Clustering con restricción espacial
- Como los polígonos no son contiguos, NO se usa Queen/Rook. Se usa **KNN y DistanceBand**
  sobre los centroides como definición de vecindad (`libpysal.weights`).
- **Optimización clave:** para explorar 2-50 clusters sin recalcular el árbol jerárquico 49
  veces por vecindad, se ajusta el modelo **una sola vez** (`compute_full_tree=True`) y se
  "corta" el árbol con una función propia (`cortar_arbol_aglomerativo`, unión-find). Se
  valida con ARI=1.000 contra el resultado directo antes de confiar en el barrido completo
  (se encontró y corrigió un bug real: faltaba unir el nodo interno del árbol, ver
  comentarios en el código).
- Heatmaps 2D (vecindad × n_clusters, paleta rojo-amarillo-verde) para **SS y CH**, tanto
  para KNN como para DistanceBand.
- Búsqueda del óptimo (vecindad, n_clusters) en la grilla completa:
  - **Mejor KNN por SS:** k=10 (o k=5 según ejecución con variables ampliadas), n_clusters=2.
  - **Mejor DistanceBand por SS:** radio=3.7 km, n_clusters=2, **pero con 319 componentes
    desconectados de 491 — resultado poco confiable** pese a tener el SS más alto. CH
    prefiere un radio muy distinto (28.1 km, solo 4 componentes) — discrepancia
    documentada explícitamente como alerta de "cautela" en el propio notebook.
- Otros diagnósticos: Índice de Rand Ajustado (ARI) entre soluciones, distancia geográfica
  promedio intra/inter-cluster (confirma que los clusters SÍ son más compactos
  geográficamente que el azar).
- Mapas finales (3 paneles): sin restricción, mejor KNN, mejor DistanceBand.
- Export: `Resultados\altiplanos_clustering_espacial.gpkg` (con columnas
  `cluster_espacial`, `cluster_mejor_knn`, `cluster_mejor_distancia`,
  `cluster_sin_restriccion`).

### `03_regresion_no_espacial_raster.ipynb` — Predicción de altiplano a nivel de píxel
- Objetivo: predecir Altiplano (1/0) por píxel usando **regresión logística NO
  espacializada** (`04_GLMPhyton` del libro) a partir de capas ráster derivadas del terreno.
- Pasos clave:
  1. Realinear `Altiplanos.tif` a la grilla del DEM (reproject nearest neighbor).
  2. Máscara de validez combinada (DEM + TODOS los predictores, no solo DEM).
  3. **VIF detectó colinealidad perfecta** (identidad `Relieve = ResidMax + ResidMin` en
     ventanas 3 y 10, y `DifMedia_5_10 = ResidMedia_5 - ResidMedia_10`) → se excluyeron
     `Relieve_3`, `Relieve_10`, `DifMedia_5_10`, quedando **18 predictores finales**.
  4. Muestra aleatoria de 300,000 píxeles (de 24.8M) para ajustar el modelo — el AJUSTE usa
     la muestra, la PREDICCIÓN final se aplica sobre los ~24.8M píxeles completos.
  5. Modelos: `statsmodels.Logit` (interpretable, Pseudo R²) + `sklearn.LogisticRegression`
     (matriz de confusión, ROC/AUC).
- **Resultados:** Pseudo R² (McFadden) = **0.551**, AUC-ROC = **0.952**, Accuracy = 0.912.
  Advertencia de `statsmodels`: **cuasi-separación completa en ~20% de las observaciones**
  (coherente con el AUC alto; implica que los p-values de coeficientes individuales deben
  tomarse con cautela, aunque la predicción sigue siendo válida).
- Mapa final de probabilidad con superposición de **bordes** (sin relleno) de los 491
  polígonos originales (`Clusters.shp`) para comparar visualmente — coincide muy bien.
- Exports: `Resultados\probabilidad_altiplano.tif` (mapa completo), figuras
  `12_correlacion_predictores_raster.png`, `13_matriz_confusion_roc.png`,
  `14_mapa_probabilidad_altiplano.png`.

### `04_autocorrelacion_espacial.ipynb` — Moran's I y LISA
Dos partes independientes, ambas del método `07_MatrizCorrelacion` del libro:

**Parte A — sobre los 491 polígonos** (KNN k=6, igual que el ejemplo del libro):
- Moran's I: `Altitud_X`=0.920, `Pend_X`=0.589, `Relieve_X`=0.484 (todos p=0.001, muy
  significativos).
- LISA de `Altitud_X`: 284/491 polígonos (58%) en clúster local significativo. Mapa muestra
  dos núcleos rojos (HH, altitud alta agrupada) que coinciden con las zonas de alta
  probabilidad del modelo raster, y clusters azules (LL) en las ramas norte/oeste.
- Export: `Resultados\altiplanos_moran_lisa.gpkg`.

**Parte B — residuos del modelo raster** (recrea la muestra de 300k píxeles del notebook
03 con la misma SEMILLA=42, KNN k=8 sobre coordenadas reales de píxel):
- Residuo usado: `y - probabilidad_predicha` (análogo al residuo OLS del libro, adaptado a
  logística).
- **Moran's I de los residuos = 0.610 (p=0.001)** → el modelo NO espacializado deja fuerte
  autocorrelación espacial sin explicar en sus errores. Esto NO invalida las métricas de
  predicción, pero motiva considerar un modelo espacial como trabajo futuro.
- LISA de residuos: patrón de **anillos** — rojo (HH, el modelo subestima) rodeando núcleos
  azules (LL, el modelo sobreestima). Hipótesis: los anillos rojos son bordes reales de
  altiplano (donde el modelo es conservador) y los núcleos azules son superficies planas NO
  delimitadas como altiplano que el modelo confunde con altiplano (falsos positivos).
- Export: `Resultados\residuos_raster_lisa_muestra.gpkg` (300,000 puntos con residuo,
  probabilidad predicha y estadísticas LISA — permite reabrir y re-estilizar sin
  reejecutar el pipeline raster completo).

### `05_modelo_jerarquico_cordilleras.ipynb` — Modelo jerárquico por cordillera
- Incorpora `Cordilleras.shp` (3 zonas: Occidental/Central/San Lucas) como nivel jerárquico
  del modelo de predicción de altiplano por píxel (`12_Jerárquico` del libro, adaptado).
  Rasterizada a la grilla del DEM con `rasterio.features.rasterize`.
- **Hallazgo motivador:** la proporción de Altiplano varía muchísimo por zona — **Central
  25.2%**, **San Lucas 16.9%**, **Occidental solo 3.8%**.
- **Bug corregido durante la construcción:** `pd.get_dummies(..., drop_first=True)` sobre
  `Zona_nombre` descarta la categoría **alfabéticamente primera** ("Central"), NO
  "Occidental" como se asumió inicialmente. Solución: forzar el orden de categorías con
  `pd.Categorical(..., categories=["Occidental","Central","SanLucas"])` antes de
  `get_dummies`, así "Occidental" queda como referencia en ambos lugares donde se generan
  dummies (muestra de entrenamiento y predicción sobre toda la tabla) — deben coincidir.
- **Comparación 2x2 rigurosa** (con/sin zona × con/sin `class_weight="balanced"`) para
  aislar qué cambio produce qué efecto:
  - El **AUC no cambia** en ninguna combinación (~0.9519–0.9525).
  - **Agregar zona sola** apenas mueve el recall de Altiplano (0.645→0.648).
  - **`class_weight="balanced"` es lo que dispara el recall de Altiplano** (0.645→0.917
    sin zona; 0.648→0.919 con zona), al costo de precisión (~0.74→~0.53).
- **Modelo operativo final:** `LogisticRegression(class_weight="balanced")` + dummies de
  zona. AUC=0.9522, Accuracy=0.865, Recall(Altiplano)=0.92, Precision(Altiplano)=0.53.
  Coeficientes de zona (odds ratio vs. Occidental): Central=1.55 (persiste tras controlar
  terreno), San Lucas=1.03 (su diferencia cruda se explica casi toda por el terreno, no por
  la zona en sí).
- **Modelo jerárquico bayesiano verdadero** (`statsmodels.BinomialBayesMixedGLM`, intercepto
  aleatorio por zona, sub-muestra de 100,000 píxeles, ajustado en ~43s): confirma
  estadísticamente varianza real entre zonas (SD del intercepto aleatorio con IC que no
  incluye 0).
- **Cuidado explícito con AUC/pos_label:** en cada modelo se verifica
  `modelo.classes_` y se usa `pos_label=1` (Altiplano) antes de calcular ROC/AUC — nunca se
  asume el orden de columnas de `predict_proba` por defecto.
- Exports: `Resultados\zonas_cordilleras.tif` (zona rasterizada),
  `Resultados\probabilidad_altiplano_jerarquico.tif` (mapa final),
  `Resultados\muestra_modelo_jerarquico.gpkg` (300k puntos con zona/predicción/probabilidad).

### `Clustering_Regiones.ipynb` — Regionalización contigua para mejorar el modelo jerárquico
- Objetivo: reemplazar las 3 Cordilleras (zonas fijas por geología/orografía) por una
  zonificación **basada en datos**, agrupando por similitud morfométrica (Altitud,
  Pendiente, Relieve_Relativo — 3 rásters nuevos, alineados pixel a pixel con el DEM) con
  **contigüidad espacial real** (Rook: cada celda solo se une a sus vecinas N/S/E/O),
  a diferencia de los 491 polígonos de altiplano (no contiguos, script 02) donde KNN/
  DistanceBand fueron un sustituto de vecindad.
- **Problema de escala:** clustering jerárquico con restricción de conectividad sobre los
  ~24.8M píxeles válidos es intratable. Solución: se agrega la grilla 20x (50m → 1 km,
  quedando 61,950 celdas válidas de 125,552), se hace el clustering ahí con
  `sklearn.feature_extraction.image.grid_to_graph` (grafo Rook, 1 solo componente
  conectado), y el resultado se reescala a 50 m con `np.repeat` (expansión de bloque
  exacta, sin reproyección) para producir un ráster de zonas al mismo grid que
  `zonas_cordilleras.tif`.
- **Se reutilizó tal cual** la función `cortar_arbol_aglomerativo` (unión-find) ya
  validada en `02_clustering_espacial_altiplanos.py`/`06_mapas_clusters_n_mayor_3.py`:
  árbol de Ward ajustado **una sola vez** (2.7s), validado con ARI=1.000 contra un ajuste
  directo antes de confiar en el barrido de k=2 a 20.
- **Silhouette (SS) necesitó muestreo** (`sample_size=5000`) por primera vez en el
  proyecto — a diferencia de los 491 polígonos, aquí el SS exacto sobre ~62,000 celdas es
  inviable. Calinski-Harabasz (CH) se calculó exacto.
- **Mismo criterio que 06/07 (`N_CLUSTERS_MINIMO=4`)**: se descartan k=2/3 al buscar el
  mejor SS porque una zonificación tan simple no mejoraría nada sobre las 3 Cordilleras ya
  existentes. Con esa restricción, **SS y CH coinciden: k=4 es el óptimo**
  (SS=0.065, CH=17869.6) — incluso el óptimo de CH sin restringir también cae en k=4.
- **Resultado:** 4 regiones contiguas y geográficamente coherentes, que NO calcan las
  fronteras de las Cordilleras (cortan el mapa en un patrón distinto, más ligado a
  altitud/pendiente/relieve que a la geología). Proporción de Altiplano por región:
  región 0=18.8%, región 1=**0.2%**, región 2=12.1%, región 3=26.8%.
  **Rango (max-min) entre zonas: 0.266 vs. 0.214 de las Cordilleras** → la nueva
  zonificación separa el fenómeno de interés mejor que las 3 Cordilleras.
- **Bug encontrado y corregido durante la construcción:** la función
  `proporcion_por_zona` excluía por error la región `0` (asumiendo la convención de
  `zonas_cordillera_raster`, donde `0` = sin zona/fill). Para el ráster de regiones el `0`
  es una etiqueta de cluster válida (el nodata real es `-1`) — se corrigió pasando un
  parámetro explícito `zona_nodata` en vez de asumir `0` siempre.
- Exports: `Resultados\zonas_clustering_regiones.tif` (reemplazo directo de
  `zonas_cordilleras.tif`), `Resultados\regiones_clustering.gpkg` (análogo a
  `Cordilleras.shp`, poligonizado desde la grilla agregada de 1 km, no desde 50 m, para
  bordes limpios).
- **Siguiente paso pendiente:** volver a ajustar el modelo jerárquico
  (`05_modelo_jerarquico_cordilleras.ipynb`) usando esta nueva zonificación en vez de
  Cordilleras, y comparar AUC/recall/precision y la varianza entre zonas (SD del
  intercepto aleatorio bayesiano) contra los resultados ya documentados.
- **Ampliación pedida por el usuario:** se agregaron gráficas de diagnóstico individuales
  (codo, Silhouette, dendrograma truncado) y dos mapas adicionales (k óptimo y k=15 "mayor
  a 10"), guardadas en la subcarpeta nueva `Resultados\Clustering_Regiones\` (separada de
  las figuras numeradas `22-25` que quedan en `Resultados\` directamente):
  `01_codo_inercia.png`, `02_silhouette_vs_k.png`, `03_dendrograma.png`,
  `04_mapa_k_optimo.png`, `05_mapa_k_mayor_10.png`.
  - El dendrograma se construye con la matriz de enlace estándar de sklearn
    (`children_` + `distances_`, requiere `compute_distances=True` en el
    `AgglomerativeClustering`) truncada a las últimas 40 fusiones (el árbol completo tiene
    61,950 hojas, imposible de graficar entero) — conviene porque los cortes de k bajo
    quedan cerca de la raíz, justo donde se trunca. Se marca con línea roja la altura de
    corte para `K_REGIONES`.
  - `K_REGIONES_MAYOR = 15` (dentro del mismo `RANGO_K` ya barrido, sin recomputar nada).
  - **El usuario pidió también la capa de k>10 como GIS real, no solo el PNG**: se agregó
    `exportar_zonas()` (generaliza la lógica de las secciones 8-9) y ahora también se
    exportan `Resultados\zonas_clustering_regiones_k15.tif` y
    `Resultados\regiones_clustering_k15.gpkg` (15 regiones), análogos a los de
    `K_REGIONES` pero para la versión más granular.

## 5. Inventario de archivos generados

### Figuras (`Resultados\*.png`, numeradas en orden de creación)
`01_correlacion_variables` · `02_seleccion_k` · `03_dendrograma` · `04_mapa_clusters` ·
`05_heatmap_perfil_clusters` · `06_dtw_vs_kmeans` · `06_silhouette_vecindad_espacial` ·
`07_mapa_comparacion_espacial` · `08_heatmap_ss_knn` · `09_heatmap_ss_distanceband` ·
`10_heatmap_ch_knn` · `11_heatmap_ch_distanceband` · `12_correlacion_predictores_raster` ·
`13_matriz_confusion_roc` · `14_mapa_probabilidad_altiplano` ·
`15_moran_scatterplot_poligonos` · `16_lisa_cluster_altitud_poligonos` ·
`17_moran_scatterplot_residuos_raster` · `18_lisa_residuos_raster` ·
`19_proporcion_altiplano_por_zona` · `20_matriz_confusion_roc_jerarquico` ·
`21_mapa_probabilidad_jerarquico` · `22_seleccion_k_regiones` ·
`23_mapa_regiones_clustering` · `24_comparacion_zonas_cordillera_vs_clustering` ·
`25_proporcion_altiplano_por_region_clustering`.

### Capas de respaldo / resultados (`Resultados\*.gpkg`, `*.tif`)
- `altiplanos_clasificados.gpkg` (script 01)
- `altiplanos_clustering_espacial.gpkg` (script 02)
- `probabilidad_altiplano.tif` (+`.ovr`) (notebook 03)
- `altiplanos_moran_lisa.gpkg` (notebook 04, parte A)
- `residuos_raster_lisa_muestra.gpkg` (notebook 04, parte B — 300k puntos)
- `zonas_cordilleras.tif`, `probabilidad_altiplano_jerarquico.tif`,
  `muestra_modelo_jerarquico.gpkg` (notebook 05)
- `zonas_clustering_regiones.tif`, `regiones_clustering.gpkg` (`Clustering_Regiones.ipynb`)

### Rásters nuevos usados por `Clustering_Regiones.ipynb` (carpeta `Raster\50m_UTM\Analisis\`)
- `Pendiente.tif` y `Relieve_Relativo.tif` — versiones únicas (no por ventana, a
  diferencia de `Slp_NA_50.tif`/`Rel_NA_3/5/10.tif`), alineadas pixel a pixel con
  `DEM_NA_50.tif` (mismo shape 8276x6084, mismo transform con diferencia de punto
  flotante ~1e-14 en el coeficiente de escala — hay que comparar transforms con
  tolerancia, no con `==` exacto, o el chequeo de alineación falla en falso positivo).

## 6. Métodos del libro — menú para continuar (Partes I-III)

**Ya cubiertos:** `08_ClusterEspacial` (K-means/Ward + regionalización KNN/DistanceBand),
`04_GLMPhyton` (regresión logística, incl. desbalanceada), `07_MatrizCorrelacion` (Moran's I
global + LISA, en polígonos y en residuos de píxel), `12_Jerárquico` (efectos fijos de zona
+ modelo bayesiano de intercepto aleatorio por cordillera).

**Con buen ajuste a los datos disponibles (candidatos para seguir):**
1. **`13_MGWR`** (GWR/Regresión Geográficamente Ponderada) — coeficientes que varían
   suavemente en el espacio, usando las coordenadas continuas de los 491 centroides (o de
   los píxeles). Complementa el modelo jerárquico por zonas discretas con una versión
   continua de la heterogeneidad espacial.
2. **`03_PointPattern`** (centrografía, KDE, Ripley G/F, DBSCAN) — tratando los 491
   centroides como patrón de puntos puro (sin atributos).
3. **`10_SAR`** a nivel de polígono (SLX/SEM/SAR-Lag) reutilizando los pesos KNN ya
   construidos, regresando una variable morfométrica contra otras.

**Descartado:** `11_CAR` — no hay contigüidad real ni zonas/conteos por zona; forzar KNN
como sustituto de adyacencia sería una desviación notable del uso previsto en el libro.

## 7. Pendiente / próximos pasos mencionados por el usuario

- El usuario indicó que **más adelante pedirá explicaciones sobre los clusters** obtenidos
  (interpretación geomorfológica de los grupos, qué significa cada uno).
- Ningún método del punto 6 se ha implementado aún — quedan como opciones abiertas a
  decidir en la próxima sesión.
