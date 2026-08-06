# %% [0] INTRODUCCION
# ============================================================================
# CLUSTERING CON RESTRICCION ESPACIAL - COMPARACION DE VECINDADES (KNN vs.
# RADIO DE DISTANCIA) - ALTIPLANOS
# ============================================================================
# Que se busca:
#   En "01_clustering_altiplanos.py" se tipificaron los 491 altiplanos usando
#   solo sus atributos morfometricos (K-means / Ward), sin ninguna nocion de
#   cercania geografica entre ellos. Aqui se pone a prueba una idea distinta:
#   ?cambia (o mejora) la tipologia si, ademas de ser morfometricamente
#   parecidos, se exige que dos altiplanos esten geograficamente cerca para
#   poder quedar en el mismo grupo?
#
#   Como los poligonos NO son contiguos (no comparten borde entre si), no se
#   puede definir vecindad con contigüidad tipo Queen/Rook (todos quedarian
#   como "isla", sin vecinos). En su lugar se define la vecindad a partir de
#   la DISTANCIA ENTRE LOS CENTROIDES de los poligonos, de dos formas
#   alternativas:
#     (a) k-vecinos mas cercanos (KNN): cada altiplano se conecta con sus
#         k centroides mas cercanos, sin importar cuan lejos esten en
#         terminos absolutos.
#     (b) radio de distancia fijo (DistanceBand): cada altiplano se conecta
#         con TODOS los centroides que esten dentro de un radio de d metros
#         (puede tener mas, menos, o incluso cero vecinos segun que tan
#         aislado este).
#
#   El script recorre varios valores de k y varios valores de d, ajusta un
#   clustering jerarquico restringido a cada vecindad, y compara el
#   coeficiente de Silhouette resultante para identificar que definicion de
#   vecindad (si alguna) produce grupos mas compactos y mejor separados que
#   el clustering sin restriccion espacial.
#
# Metodo del libro utilizado:
#   Notebook "08_ClusterEspacial", seccion de "Agrupamiento espacial
#   (Regionalizacion)". El libro usa AgglomerativeClustering con el
#   parametro connectivity=w.sparse (la matriz de pesos convertida a matriz
#   dispersa) y compara puntualmente el Silhouette obtenido con una matriz
#   KNN (k=6) contra una matriz DistanceBand (30 km) para el dataset de
#   cuencas colombianas. Aqui se generaliza esa comparacion puntual a un
#   barrido sistematico de muchos valores de k y de d, en vez de probar un
#   solo valor de cada uno "a ojo".
#
# Nota sobre el Área:
#   Por instruccion explicita, el Área NO se incluye en ningun analisis de
#   este script: ni en las variables de clustering (igual que en
#   "01_clustering_altiplanos.py") ni en ninguna tabla de perfilamiento.
# ============================================================================

import struct
import os
import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score, calinski_harabasz_score, adjusted_rand_score

from libpysal.weights import KNN, DistanceBand

# Configuracion general de rutas del proyecto
RUTA_SHP = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Capas\Estadisticas_Cluster.shp"
RUTA_DBF = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Capas\Estadisticas_Cluster.dbf"
CARPETA_RESULTADOS = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Resultados"

SEMILLA = 42
K_ELEGIDO = 4  # numero de grupos finales; usar el mismo valor que en 01_clustering_altiplanos.py para poder comparar


# %% [1] UTILIDAD: CORRECCION DE CODIFICACION DEL DBF
# ----------------------------------------------------------------------------
# Misma utilidad que en "01_clustering_altiplanos.py": los NOMBRES de
# columna del .dbf llegan corruptos porque pyogrio/GDAL no aplica a los
# nombres de campo el encoding UTF-8 declarado en el .cpg (si aplica a los
# valores). Se leen los nombres directamente del encabezado binario.
# ----------------------------------------------------------------------------
def nombres_reales_columnas_dbf(ruta_dbf: str, encoding: str = "utf-8") -> list[str]:
    with open(ruta_dbf, "rb") as f:
        encabezado = f.read(32)
        tam_encabezado = struct.unpack("<H", encabezado[8:10])[0]
        f.seek(0)
        encabezado_completo = f.read(tam_encabezado)

    nombres = []
    offset = 32
    while True:
        descriptor = encabezado_completo[offset:offset + 32]
        if descriptor[0:1] == b"\x0d" or len(descriptor) < 32:
            break
        crudo = descriptor[0:11].split(b"\x00")[0]
        nombres.append(crudo.decode(encoding))
        offset += 32
    return nombres


# %% [2] CARGA DE DATOS Y VARIABLES DE CLUSTERING
# ----------------------------------------------------------------------------
# Mismas 9 variables morfometricas de "01_clustering_altiplanos.py" (medias y
# desviaciones estandar de altitud, relieve y pendiente, mas los percentiles
# de altitud Alt_90/Alt_50/Alt_10 que ya trae la tabla de datos), estandarizadas
# de la misma forma. El Área queda excluida (ver justificacion en el script
# "01_clustering_altiplanos.py", seccion [4]).
# ----------------------------------------------------------------------------
gdf = gpd.read_file(RUTA_SHP)
gdf.columns = nombres_reales_columnas_dbf(RUTA_DBF) + ["geometry"]

variables_cluster = [
    "Altitud_X", "Altitud_St", "Alt_90", "Alt_50", "Alt_10",
    "Relieve_X", "Relieve_St", "Pend_X", "Pend_St",
]

escalador = StandardScaler()
X = escalador.fit_transform(gdf[variables_cluster])

print(f"Poligonos cargados: {len(gdf)}")
print(f"Variables de clustering (sin Área): {variables_cluster}")


# %% [3] DIAGNOSTICO: DISTANCIA ENTRE CENTROIDES VECINOS
# ----------------------------------------------------------------------------
# Que se busca:
#   Antes de "adivinar" un radio de distancia para DistanceBand, conviene
#   conocer la escala real de las distancias entre los altiplanos. Se
#   calcula, para cada poligono, la distancia a su centroide vecino MAS
#   cercano (usando un KD-Tree sobre los centroides). El CRS del shapefile
#   (EPSG:32618) es una proyeccion plana EN METROS, asi que todo calculo e
#   insumo que se le pase a libpysal (KNN, DistanceBand) se sigue haciendo
#   internamente en metros; los KILOMETROS solo se usan para MOSTRAR los
#   resultados (impresos, tablas y graficos), por ser una unidad mas legible
#   a esta escala (los altiplanos estan separados por unos pocos km a unas
#   pocas decenas de km, no por miles de metros "sueltos").
#   Los percentiles de esa distribucion se usan para proponer un rango de
#   radios candidatos con sentido para este conjunto de datos especifico,
#   en vez de proponer numeros arbitrarios.
# ----------------------------------------------------------------------------
centroides = gdf.geometry.centroid
coordenadas = np.column_stack([centroides.x, centroides.y])

arbol = cKDTree(coordenadas)
# k=2 porque el vecino "0" de cada punto es el mismo punto (distancia 0)
distancias, _ = arbol.query(coordenadas, k=2)
distancia_vecino_mas_cercano = distancias[:, 1]

print("\nDistancia al centroide vecino mas cercano (km):")
percentiles = [0, 10, 25, 50, 75, 90, 95, 99, 100]
resumen_distancias = np.percentile(distancia_vecino_mas_cercano, percentiles)
for p, valor in zip(percentiles, resumen_distancias):
    print(f"  percentil {p:>3}: {valor / 1000:>8,.2f} km")

# Radios candidatos: percentiles 50/75/90/95/99 de la distancia al vecino
# mas cercano, redondeados a la centena de metros para que sean legibles,
# mas un radio "amplio" (percentil 100, la maxima distancia observada) que
# garantiza que ningun poligono quede sin vecinos.
# IMPORTANTE: esta lista queda en METROS porque es la unidad que espera
# libpysal.weights.DistanceBand (debe coincidir con las unidades del CRS
# proyectado). La version en km (radios_candidatos_km) es solo para mostrar.
radios_candidatos = sorted(set(
    int(round(v, -2)) for v in np.percentile(distancia_vecino_mas_cercano, [50, 60, 70, 80, 90, 95, 99, 100])
))
radios_candidatos_km = [round(r / 1000, 1) for r in radios_candidatos]
print(f"\nRadios candidatos derivados de los datos (km): {radios_candidatos_km}")

# Numero de vecinos (k) candidatos para KNN: de muy local (k=3) a bastante
# amplio (k=40, ~8% del total de poligonos).
vecinos_candidatos = [3, 4, 5, 6, 8, 10, 15, 20, 30, 40]


# %% [4] LINEA BASE: CLUSTERING SIN RESTRICCION ESPACIAL
# ----------------------------------------------------------------------------
# Que se busca: tener un punto de referencia. Se usa el MISMO algoritmo
# (Ward aglomerativo) y el MISMO numero de grupos (K_ELEGIDO) que se usara
# con las restricciones espaciales, pero sin ninguna matriz de conectividad
# (connectivity=None), para que la unica diferencia entre esta corrida y
# las siguientes sea la restriccion de vecindad, y no el algoritmo en si.
# ----------------------------------------------------------------------------
modelo_base = AgglomerativeClustering(n_clusters=K_ELEGIDO, linkage="ward")
etiquetas_base = modelo_base.fit_predict(X)
silhouette_base = silhouette_score(X, etiquetas_base)

print(f"\nSilhouette SIN restriccion espacial (linea base): {silhouette_base:.3f}")


# %% [5] BARRIDO KNN: SILHOUETTE PARA CADA NUMERO DE VECINOS
# ----------------------------------------------------------------------------
# Que se busca: para cada valor de k en vecinos_candidatos, construir la
# matriz de pesos KNN entre centroides, forzar a que el clustering
# jerarquico solo pueda fusionar altiplanos conectados en esa matriz, y
# medir el Silhouette resultante (calculado siempre en el espacio de las
# variables estandarizadas, no en el espacio geografico).
#
# Ventajas / desventajas de KNN como definicion de vecindad:
#   (+) Todo poligono queda garantizado con exactamente k vecinos, sin
#       importar que tan denso o disperso sea su entorno -> nunca hay
#       "islas" (poligonos sin ningun vecino).
#   (-) En zonas muy dispersas, el k-esimo vecino mas cercano puede estar a
#       decenas o cientos de kilometros, lo cual no es realmente "cercano"
#       en un sentido geografico; KNN no distingue eso.
#   (-) La relacion de vecindad no es simetrica en general (que B sea uno
#       de los k vecinos mas cercanos de A no garantiza que A sea uno de
#       los k vecinos mas cercanos de B); aqui se simetriza la matriz antes
#       de usarla como conectividad, tomando el maximo entre la matriz y su
#       transpuesta.
# ----------------------------------------------------------------------------
def simetrizar(matriz_dispersa):
    """Combina una matriz de adyacencia con su transpuesta (A es vecino de B
    O B es vecino de A -> quedan conectados), para un grafo de conectividad
    bien definido en AgglomerativeClustering."""
    return matriz_dispersa.maximum(matriz_dispersa.T)


resultados_knn = []
with warnings.catch_warnings():
    warnings.simplefilter("ignore")  # silencia avisos de libpysal/sklearn sobre grafos desconectados
    for k in vecinos_candidatos:
        w_knn = KNN.from_dataframe(gdf, k=k)
        conectividad = simetrizar(w_knn.sparse)
        n_componentes, _ = connected_components(conectividad, directed=False)

        modelo = AgglomerativeClustering(n_clusters=K_ELEGIDO, linkage="ward", connectivity=conectividad)
        etiquetas = modelo.fit_predict(X)
        silueta = silhouette_score(X, etiquetas)

        resultados_knn.append({
            "k_vecinos": k,
            "silhouette": silueta,
            "n_componentes_conectados": n_componentes,
        })

resultados_knn = pd.DataFrame(resultados_knn)
print("\nResultados KNN (numero de vecinos vs. Silhouette):")
print(resultados_knn)


# %% [6] BARRIDO DISTANCEBAND: SILHOUETTE PARA CADA RADIO
# ----------------------------------------------------------------------------
# Que se busca: lo mismo que el paso anterior, pero definiendo la vecindad
# por un radio fijo en metros en vez de un numero fijo de vecinos.
#
# Ventajas / desventajas de DistanceBand como definicion de vecindad:
#   (+) Tiene una interpretacion geografica directa y facil de comunicar
#       ("altiplanos a menos de d metros uno del otro"), a diferencia de
#       KNN donde k no tiene una lectura fisica directa.
#   (-) Un mismo radio puede dejar a poligonos en zonas dispersas sin
#       NINGUN vecino ("islas"); cuando eso ocurre, el grafo de
#       conectividad queda fragmentado en varias componentes separadas, y
#       AgglomerativeClustering necesita conectarlas artificialmente para
#       poder fusionar todo en K_ELEGIDO grupos (esto se reporta abajo como
#       "n_componentes_conectados": entre mas alto ese numero, mas forzada
#       y menos confiable es la fusion final para ese radio).
# ----------------------------------------------------------------------------
resultados_distancia = []
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in radios_candidatos:
        w_dist = DistanceBand.from_dataframe(gdf, threshold=d, binary=True)
        conectividad = simetrizar(w_dist.sparse)
        n_componentes, _ = connected_components(conectividad, directed=False)

        modelo = AgglomerativeClustering(n_clusters=K_ELEGIDO, linkage="ward", connectivity=conectividad)
        etiquetas = modelo.fit_predict(X)
        silueta = silhouette_score(X, etiquetas)

        resultados_distancia.append({
            "radio_m": d,  # metros: se conserva para volver a construir la matriz de pesos con libpysal
            "radio_km": round(d / 1000, 1),  # kilometros: solo para mostrar en tablas/graficos
            "silhouette": silueta,
            "n_componentes_conectados": n_componentes,
            "n_islas_sin_vecinos": len(w_dist.islands),
        })

resultados_distancia = pd.DataFrame(resultados_distancia)
print("\nResultados DistanceBand (radio vs. Silhouette):")
print(resultados_distancia)


# %% [7] COMPARACION GRAFICA: KNN vs. DISTANCEBAND vs. LINEA BASE
# ----------------------------------------------------------------------------
# Que se busca: visualizar en un solo par de graficos como varia el
# Silhouette al cambiar el parametro de vecindad, con una linea horizontal
# de referencia que marca el Silhouette del clustering SIN restriccion
# espacial (paso 4). Si ningun punto supera esa linea, la conclusion es que
# imponer una restriccion espacial no mejora (e incluso empeora) la
# compacidad/separacion de los grupos para este conjunto de datos.
# ----------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

ax1.plot(resultados_knn["k_vecinos"], resultados_knn["silhouette"], marker="o", color="steelblue")
ax1.axhline(silhouette_base, color="gray", linestyle="--", label=f"Sin restriccion espacial ({silhouette_base:.3f})")
ax1.set_xlabel("Numero de vecinos (k) - KNN")
ax1.set_ylabel("Coeficiente de Silhouette")
ax1.set_title("Vecindad por KNN")
ax1.legend(fontsize=8)

ax2.plot(resultados_distancia["radio_km"], resultados_distancia["silhouette"], marker="o", color="darkorange")
ax2.axhline(silhouette_base, color="gray", linestyle="--", label=f"Sin restriccion espacial ({silhouette_base:.3f})")
ax2.set_xlabel("Radio de distancia (km) - DistanceBand")
ax2.set_ylabel("Coeficiente de Silhouette")
ax2.set_title("Vecindad por radio de distancia")
ax2.legend(fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "06_silhouette_vecindad_espacial.png"), dpi=150)
plt.show()


# %% [8] MAPAS DE CALOR: SS SEGUN VECINDAD (eje Y) Y NUMERO DE CLUSTERS (eje X)
# ----------------------------------------------------------------------------
# Que se busca:
#   Las secciones 5, 6 y 7 fijaron el numero de clusters en K_ELEGIDO y solo
#   variaron el parametro de vecindad (k o radio). Pero la eleccion de
#   cuantos clusters formar es en si misma otra decision que afecta el
#   Silhouette (SS), y las dos decisiones (vecindad y n. de clusters) pueden
#   interactuar: una vecindad que se ve mediocre con 4 clusters podria ser
#   la mejor opcion con 6. Este mapa de calor cruza AMBAS decisiones a la
#   vez -vecindad en el eje Y, numero de clusters en el eje X- para no
#   optimizar cada parametro por separado de forma potencialmente enganosa.
#
# Metodo del libro utilizado:
#   Extension directa de la comparacion de "08_ClusterEspacial" (SS para
#   distintas matrices de pesos) combinada con la logica del metodo del
#   codo/Silhouette de la Actividad 1 del mismo notebook (SS para distintos
#   k). Aqui se combinan ambos barridos en una sola matriz de resultados en
#   lugar de dos barridos independientes.
#
# Ventajas / desventajas de este mapa de calor combinado:
#   (+) Permite detectar visualmente si existe una "region" de la grilla
#       (una combinacion vecindad + n_clusters) consistentemente buena, en
#       vez de conclusiones basadas en un unico corte fijo de n_clusters.
#   (-) Con radios de DistanceBand pequeños y pocos clusters, algunas
#       combinaciones pueden fallar (grafo demasiado fragmentado) y quedan
#       como celdas vacias (NaN, en blanco) en el mapa.
#   (-) Con 491 poligonos en total, pedir 50 clusters implica grupos de
#       menos de 10 altiplanos en promedio; mas alla de cierto punto (ver
#       columnas de la derecha del mapa) el SS deja de reflejar "tipos"
#       geomorfologicos genuinos y empieza a aislar observaciones sueltas.
#
# Nota de optimizacion (importante para que esto corra en tiempo razonable):
#   Ampliar el eje X de 9 a 49 valores de n_clusters (2 a 50) NO se hizo
#   simplemente repitiendo 49 veces el ajuste de AgglomerativeClustering por
#   cada vecindad (eso multiplicaria por ~5 el tiempo ya observado con 9
#   valores, es decir, decenas de minutos). En su lugar se aprovecha que,
#   para una MISMA matriz de conectividad, el orden en que Ward fusiona los
#   poligonos NO depende de en que numero de clusters se decida "cortar" el
#   arbol de fusiones. Por eso el modelo se ajusta UNA sola vez por vecindad
#   pidiendole el arbol completo (compute_full_tree=True), y luego se corta
#   ese mismo arbol ya calculado para cada uno de los 49 valores de
#   n_clusters con una funcion propia (cortar_arbol_aglomerativo), en vez de
#   reajustar el modelo desde cero cada vez. Esto reduce los ajustes reales
#   de clustering de (10+8) x 49 = 882 a solo 10+8 = 18, y el resto son
#   simples "cortes" del arbol (mucho mas baratos).
# ----------------------------------------------------------------------------
rango_n_clusters = list(range(2, 51))  # de 2 a 50 clusters


def cortar_arbol_aglomerativo(children, n_muestras, n_clusters):
    """Reconstruye las etiquetas de cluster para CUALQUIER n_clusters a
    partir del arbol de fusiones (children_) de un AgglomerativeClustering
    ya ajustado con compute_full_tree=True, sin necesidad de reajustar el
    modelo. Es equivalente a haber llamado fit_predict con ese n_clusters
    directamente, porque el orden de fusion de Ward no cambia segun donde
    se decida cortar el arbol; aqui solo se "deshacen" las ultimas fusiones
    en vez de recalcularlas.
    """
    # Union-Find (conjuntos disjuntos) sobre todos los nodos del arbol: las
    # n_muestras hojas originales (0..n_muestras-1) mas los nodos internos
    # que se van creando en cada fusion (n_muestras..2*n_muestras-2).
    padre = list(range(2 * n_muestras - 1))

    def encontrar(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def unir(x, y):
        rx, ry = encontrar(x), encontrar(y)
        if rx != ry:
            padre[ry] = rx

    # Aplicar solo las primeras (n_muestras - n_clusters) fusiones, es decir
    # las mas tempranas/locales del arbol; las fusiones restantes (mas
    # arriba en el arbol, que unirian grupos ya grandes) se "ignoran" para
    # quedarnos con mas clusters en vez de menos.
    # OJO: ademas de unir los dos elementos fusionados (a, b) entre si, hay
    # que unir tambien el NUEVO nodo interno que sklearn crea para
    # representar a ese grupo (indice n_muestras + i), porque fusiones
    # posteriores del arbol pueden referirse a "n_muestras + i" en vez de a
    # los elementos originales. Omitir esta segunda union deja ese nodo
    # interno desconectado del grupo real y produce un corte incorrecto
    # (se detecto justamente con la validacion ARI de la seccion anterior).
    n_fusiones = n_muestras - n_clusters
    for i in range(n_fusiones):
        a, b = int(children[i, 0]), int(children[i, 1])
        unir(a, b)
        unir(a, n_muestras + i)

    raices = np.array([encontrar(j) for j in range(n_muestras)])
    _, etiquetas = np.unique(raices, return_inverse=True)
    return etiquetas


def barrido_metricas_2d(valores_vecindad, construir_pesos, rango_n_clusters, X):
    """Recorre cada valor de vecindad (k o radio), construye su matriz de
    conectividad y AJUSTA EL MODELO UNA SOLA VEZ pidiendo el arbol completo
    de fusiones; luego reutiliza ese arbol para evaluar DOS criterios de
    validacion (Silhouette y Calinski-Harabasz) en cada numero de clusters
    de rango_n_clusters mediante cortar_arbol_aglomerativo, sin volver a
    llamar fit(). Calinski-Harabasz se calcula "gratis" en el mismo barrido
    porque reutiliza las mismas etiquetas ya cortadas del arbol, y es mucho
    mas barato que Silhouette (no exige comparar cada par de observaciones).
    Devuelve dos matrices (filas=vecindad, columnas=n_clusters), una por
    criterio, con NaN donde una combinacion no pudo evaluarse."""
    n_muestras = X.shape[0]
    matriz_ss = np.full((len(valores_vecindad), len(rango_n_clusters)), np.nan)
    matriz_ch = np.full((len(valores_vecindad), len(rango_n_clusters)), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i, valor_vecindad in enumerate(valores_vecindad):
            try:
                conectividad = simetrizar(construir_pesos(valor_vecindad).sparse)
                # n_clusters=2 aqui es solo un valor minimo valido para que
                # sklearn acepte la llamada; compute_full_tree=True fuerza a
                # construir TODAS las fusiones (no solo hasta llegar a 2),
                # que es lo que permite despues cortar en cualquier k.
                modelo = AgglomerativeClustering(
                    n_clusters=2, linkage="ward", connectivity=conectividad, compute_full_tree=True
                ).fit(X)
            except Exception:
                continue  # esa vecindad no se pudo construir/ajustar; fila queda en NaN
            for j, n_clusters in enumerate(rango_n_clusters):
                try:
                    etiquetas = cortar_arbol_aglomerativo(modelo.children_, n_muestras, n_clusters)
                    if len(np.unique(etiquetas)) < 2:
                        continue  # las metricas no estan definidas con un solo cluster
                    matriz_ss[i, j] = silhouette_score(X, etiquetas)
                    matriz_ch[i, j] = calinski_harabasz_score(X, etiquetas)
                except Exception:
                    continue  # combinacion no evaluable; celda en NaN
    return matriz_ss, matriz_ch


# Validacion rapida: confirmar que "ajustar una vez y cortar" da el MISMO
# resultado que ajustar directamente con ese n_clusters (metodo usado en
# las secciones 5-6). Se compara para un caso conocido antes de confiar en
# el barrido completo.
_conectividad_prueba = simetrizar(KNN.from_dataframe(gdf, k=6).sparse)
_directo = AgglomerativeClustering(
    n_clusters=K_ELEGIDO, linkage="ward", connectivity=_conectividad_prueba
).fit_predict(X)
_arbol_completo = AgglomerativeClustering(
    n_clusters=2, linkage="ward", connectivity=_conectividad_prueba, compute_full_tree=True
).fit(X)
_cortado = cortar_arbol_aglomerativo(_arbol_completo.children_, X.shape[0], K_ELEGIDO)
_ari_validacion = adjusted_rand_score(_directo, _cortado)
print(f"\nValidacion del atajo 'ajustar una vez y cortar' (debe ser 1.000): ARI={_ari_validacion:.3f}")
assert _ari_validacion == 1.0, "El atajo de corte de arbol no reproduce el resultado directo; revisar la logica."

matriz_ss_knn, matriz_ch_knn = barrido_metricas_2d(
    vecinos_candidatos, lambda k: KNN.from_dataframe(gdf, k=k), rango_n_clusters, X
)
matriz_ss_distancia, matriz_ch_distancia = barrido_metricas_2d(
    radios_candidatos, lambda d: DistanceBand.from_dataframe(gdf, threshold=d, binary=True), rango_n_clusters, X
)

# Paleta pedida: rojo (SS=0) - amarillo (intermedio) - verde (SS=1).
# La colormap de matplotlib "RdYlGn" ya sigue exactamente esa secuencia.
# Nota: con el eje X ampliado a 49 valores (2 a 50 clusters), ya no se
# anotan los valores numericos dentro de cada celda (con 10x49=490 o
# 8x49=392 celdas el texto quedaria ilegible); el valor de SS lo comunica
# el color, apoyado por la barra de color de referencia (0 a 1).
PALETA_SS = "RdYlGn"
TICKS_X_CLUSTERS = list(range(0, len(rango_n_clusters), 4))  # posiciones: cada 4 valores de n_clusters (2, 6, 10, ...)
ETIQUETAS_X_CLUSTERS = [rango_n_clusters[i] for i in TICKS_X_CLUSTERS]

fig_knn, ax_knn = plt.subplots(figsize=(14, 5))
sns.heatmap(
    matriz_ss_knn,
    xticklabels=False,
    yticklabels=vecinos_candidatos,
    cmap=PALETA_SS,
    vmin=0,
    vmax=1,
    annot=False,
    linewidths=0.3,
    cbar_kws={"label": "Silhouette Score (SS)"},
    ax=ax_knn,
)
ax_knn.set_xticks([t + 0.5 for t in TICKS_X_CLUSTERS])
ax_knn.set_xticklabels(ETIQUETAS_X_CLUSTERS, rotation=0)
ax_knn.set_xlabel("Numero de clusters")
ax_knn.set_ylabel("Numero de vecinos (k) - KNN")
ax_knn.set_title("SS segun vecindad KNN y numero de clusters (2 a 50)")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "08_heatmap_ss_knn.png"), dpi=150)
plt.show()

fig_dist, ax_dist = plt.subplots(figsize=(14, 5))
sns.heatmap(
    matriz_ss_distancia,
    xticklabels=False,
    yticklabels=radios_candidatos_km,
    cmap=PALETA_SS,
    vmin=0,
    vmax=1,
    annot=False,
    linewidths=0.3,
    cbar_kws={"label": "Silhouette Score (SS)"},
    ax=ax_dist,
)
ax_dist.set_xticks([t + 0.5 for t in TICKS_X_CLUSTERS])
ax_dist.set_xticklabels(ETIQUETAS_X_CLUSTERS, rotation=0)
ax_dist.set_xlabel("Numero de clusters")
ax_dist.set_ylabel("Radio de distancia (km) - DistanceBand")
ax_dist.set_title("SS segun vecindad por radio y numero de clusters (2 a 50)")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "09_heatmap_ss_distanceband.png"), dpi=150)
plt.show()

# ----------------------------------------------------------------------------
# Mismos mapas de calor pero con el indice de Calinski-Harabasz (CH), como
# segunda "condicion" de validacion de clusters (ver justificacion completa
# en "01_clustering_altiplanos.py", seccion [6]). A diferencia del SS, el CH
# no tiene un rango fijo entre 0 y 1 (es una razon de varianzas sin cota
# superior), asi que la escala de color se ajusta al minimo/maximo real de
# cada matriz en vez de usar vmin=0, vmax=1.
# ----------------------------------------------------------------------------
fig_ch_knn, ax_ch_knn = plt.subplots(figsize=(14, 5))
sns.heatmap(
    matriz_ch_knn,
    xticklabels=False,
    yticklabels=vecinos_candidatos,
    cmap=PALETA_SS,
    annot=False,
    linewidths=0.3,
    cbar_kws={"label": "Indice de Calinski-Harabasz (CH)"},
    ax=ax_ch_knn,
)
ax_ch_knn.set_xticks([t + 0.5 for t in TICKS_X_CLUSTERS])
ax_ch_knn.set_xticklabels(ETIQUETAS_X_CLUSTERS, rotation=0)
ax_ch_knn.set_xlabel("Numero de clusters")
ax_ch_knn.set_ylabel("Numero de vecinos (k) - KNN")
ax_ch_knn.set_title("Calinski-Harabasz segun vecindad KNN y numero de clusters (2 a 50)")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "10_heatmap_ch_knn.png"), dpi=150)
plt.show()

fig_ch_dist, ax_ch_dist = plt.subplots(figsize=(14, 5))
sns.heatmap(
    matriz_ch_distancia,
    xticklabels=False,
    yticklabels=radios_candidatos_km,
    cmap=PALETA_SS,
    annot=False,
    linewidths=0.3,
    cbar_kws={"label": "Indice de Calinski-Harabasz (CH)"},
    ax=ax_ch_dist,
)
ax_ch_dist.set_xticks([t + 0.5 for t in TICKS_X_CLUSTERS])
ax_ch_dist.set_xticklabels(ETIQUETAS_X_CLUSTERS, rotation=0)
ax_ch_dist.set_xlabel("Numero de clusters")
ax_ch_dist.set_ylabel("Radio de distancia (km) - DistanceBand")
ax_ch_dist.set_title("Calinski-Harabasz segun vecindad por radio y numero de clusters (2 a 50)")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "11_heatmap_ch_distanceband.png"), dpi=150)
plt.show()


# %% [9] MEJOR (VECINDAD, N_CLUSTERS) PARA CADA MODELO - BUSQUEDA EN LA GRILLA COMPLETA
# ----------------------------------------------------------------------------
# Que se busca:
#   Las secciones 5-7 comparaban las vecindades con el numero de clusters
#   FIJO en K_ELEGIDO. Ahora que se tiene la grilla completa (secciones 8),
#   se busca, por separado para KNN y para DistanceBand, la combinacion
#   (vecindad, n_clusters) que maximiza el Silhouette en TODA la grilla (no
#   solo en la fila/columna de K_ELEGIDO). Esto responde directamente la
#   pregunta de "cual es el mejor modelo para numero de vecinos" y "cual es
#   el mejor modelo para numero de distancia", cada uno con su propio numero
#   de clusters optimo (no necesariamente el mismo entre ambos, ni el mismo
#   que K_ELEGIDO).
#
# Ventajas / desventajas de optimizar sobre la grilla completa:
#   (+) No se fuerza a las dos vecindades a compararse en un unico numero de
#       clusters arbitrario (K_ELEGIDO); cada una encuentra su mejor "resolucion".
#   (-) Riesgo de comparaciones multiples: entre mas combinaciones se prueban
#       (aqui hasta 10x49=490 para KNN y 8x49=392 para DistanceBand), mas
#       probable es encontrar un maximo alto "por azar" en vez de una mejora
#       genuina. Por eso se reporta tambien que tanto coincide el optimo de
#       Silhouette con el de Calinski-Harabasz (un desacuerdo grande entre
#       ambos criterios es una señal de alerta de que el maximo encontrado
#       podria no ser robusto).
#   (-) Como se vio en el barrido 1D (seccion 7), el Silhouette tiende a ser
#       mas alto con POCOS clusters (n_clusters=2-4); by conviene revisar si
#       el optimo encontrado cae en esa zona antes de aceptarlo sin mas.
# ----------------------------------------------------------------------------
def mejor_combinacion(matriz, valores_vecindad, rango_n_clusters):
    """Devuelve (indice_fila, indice_columna, valor) del maximo de la matriz,
    ignorando NaN."""
    if np.all(np.isnan(matriz)):
        return None, None, np.nan
    idx_plano = np.nanargmax(matriz)
    i, j = np.unravel_index(idx_plano, matriz.shape)
    return i, j, matriz[i, j]


# --- KNN: mejor combinacion segun SS, y segun CH para comparar ---
i_ss, j_ss, ss_max_knn = mejor_combinacion(matriz_ss_knn, vecinos_candidatos, rango_n_clusters)
i_ch, j_ch, ch_max_knn = mejor_combinacion(matriz_ch_knn, vecinos_candidatos, rango_n_clusters)
mejor_k_knn = vecinos_candidatos[i_ss]
mejor_nclusters_knn = rango_n_clusters[j_ss]
mejor_k_knn_ch = vecinos_candidatos[i_ch]
mejor_nclusters_knn_ch = rango_n_clusters[j_ch]

print(f"\n[KNN] Mejor combinacion segun SS: k={mejor_k_knn}, n_clusters={mejor_nclusters_knn} (SS={ss_max_knn:.3f})")
print(f"[KNN] Mejor combinacion segun CH: k={mejor_k_knn_ch}, n_clusters={mejor_nclusters_knn_ch} (CH={ch_max_knn:.1f})")
if (mejor_k_knn, mejor_nclusters_knn) != (mejor_k_knn_ch, mejor_nclusters_knn_ch):
    print("  -> SS y Calinski-Harabasz NO coinciden en el optimo; tomar el resultado con cautela.")

# --- DistanceBand: mejor combinacion segun SS, y segun CH para comparar ---
i_ss_d, j_ss_d, ss_max_dist = mejor_combinacion(matriz_ss_distancia, radios_candidatos, rango_n_clusters)
i_ch_d, j_ch_d, ch_max_dist = mejor_combinacion(matriz_ch_distancia, radios_candidatos, rango_n_clusters)
mejor_radio_dist = radios_candidatos[i_ss_d]
mejor_nclusters_dist = rango_n_clusters[j_ss_d]
mejor_radio_dist_ch = radios_candidatos[i_ch_d]
mejor_nclusters_dist_ch = rango_n_clusters[j_ch_d]

print(f"\n[DistanceBand] Mejor combinacion segun SS: radio={mejor_radio_dist/1000:.1f} km, "
      f"n_clusters={mejor_nclusters_dist} (SS={ss_max_dist:.3f})")
print(f"[DistanceBand] Mejor combinacion segun CH: radio={mejor_radio_dist_ch/1000:.1f} km, "
      f"n_clusters={mejor_nclusters_dist_ch} (CH={ch_max_dist:.1f})")
if (mejor_radio_dist, mejor_nclusters_dist) != (mejor_radio_dist_ch, mejor_nclusters_dist_ch):
    print("  -> SS y Calinski-Harabasz NO coinciden en el optimo; tomar el resultado con cautela.")

# Se recalculan las etiquetas finales de cada modelo ganador (KNN y
# DistanceBand), cada uno con SU PROPIO numero optimo de clusters.
w_ganador_knn = KNN.from_dataframe(gdf, k=mejor_k_knn)
conectividad_ganadora_knn = simetrizar(w_ganador_knn.sparse)
etiquetas_mejor_knn = AgglomerativeClustering(
    n_clusters=mejor_nclusters_knn, linkage="ward", connectivity=conectividad_ganadora_knn
).fit_predict(X)

w_ganador_dist = DistanceBand.from_dataframe(gdf, threshold=mejor_radio_dist, binary=True)
conectividad_ganadora_dist = simetrizar(w_ganador_dist.sparse)
etiquetas_mejor_dist = AgglomerativeClustering(
    n_clusters=mejor_nclusters_dist, linkage="ward", connectivity=conectividad_ganadora_dist
).fit_predict(X)

gdf["cluster_mejor_knn"] = etiquetas_mejor_knn
gdf["cluster_mejor_distancia"] = etiquetas_mejor_dist

# Para las secciones siguientes (ARI, diagnostico de distancia), se usa como
# "ganador global" el que tenga el SS mas alto entre KNN y DistanceBand.
if ss_max_knn >= ss_max_dist:
    etiquetas_finales = etiquetas_mejor_knn
    mejor_global_desc = f"KNN (k={mejor_k_knn}, n_clusters={mejor_nclusters_knn})"
    mejor_global_ss = ss_max_knn
else:
    etiquetas_finales = etiquetas_mejor_dist
    mejor_global_desc = f"DistanceBand (radio={mejor_radio_dist/1000:.1f} km, n_clusters={mejor_nclusters_dist})"
    mejor_global_ss = ss_max_dist

print(f"\n>> Mejor configuracion global (entre KNN y DistanceBand): {mejor_global_desc}, Silhouette={mejor_global_ss:.3f}")
print(f">> Linea base sin restriccion espacial (K_ELEGIDO={K_ELEGIDO}): Silhouette={silhouette_base:.3f}")

gdf["cluster_espacial"] = etiquetas_finales


# %% [10] OTROS ANALISIS PERTINENTES
# ----------------------------------------------------------------------------
# (a) Indice de Rand Ajustado (ARI): compara la particion ganadora contra
#     la particion SIN restriccion espacial para cuantificar que tanto
#     cambio realmente la tipologia (1.0 = particiones identicas,
#     0.0 = tan distintas como una asignacion al azar). Un ARI alto
#     significa que la restriccion espacial fue "cosmetica" (no cambio casi
#     nada la tipologia); un ARI bajo significa que si reorganizo bastante
#     los grupos.
#
# (b) Diagnostico espacial simple: ?los altiplanos de un mismo cluster
#     quedaron ademas mas cerca geograficamente entre si que altiplanos de
#     clusters distintos? Se calcula la distancia promedio entre centroides
#     DENTRO de cada cluster y se compara contra la distancia promedio
#     ENTRE clusters. Esto es justamente lo que el Silhouette (calculado en
#     el espacio de atributos) no puede decirnos: si la solucion ganadora
#     realmente quedo mas "compacta" en el mapa, no solo en el espacio de
#     variables morfometricas.
# ----------------------------------------------------------------------------
ari = adjusted_rand_score(etiquetas_base, etiquetas_finales)
print(f"\nIndice de Rand Ajustado (ganadora vs. sin restriccion espacial): {ari:.3f}")

# Distancia geografica promedio dentro y entre clusters (usando las
# coordenadas de los centroides calculadas en el paso 3).
from scipy.spatial.distance import pdist, squareform

matriz_distancias = squareform(pdist(coordenadas))
n = len(gdf)
mismo_cluster = etiquetas_finales[:, None] == etiquetas_finales[None, :]
np.fill_diagonal(mismo_cluster, False)  # no comparar un poligono consigo mismo

dist_dentro = matriz_distancias[mismo_cluster].mean()
dist_entre = matriz_distancias[~mismo_cluster].mean()
print(f"Distancia promedio ENTRE CENTROIDES dentro del mismo cluster: {dist_dentro / 1000:,.1f} km")
print(f"Distancia promedio ENTRE CENTROIDES de clusters distintos:   {dist_entre / 1000:,.1f} km")
if dist_dentro < dist_entre:
    print("-> Los altiplanos del mismo tipo SI tienden a estar mas cerca entre si que los de tipos distintos.")
else:
    print("-> Los altiplanos del mismo tipo NO estan mas cerca entre si; el patron es principalmente morfometrico, no geografico.")


# %% [11] MAPAS: LINEA BASE, MEJOR KNN Y MEJOR DISTANCEBAND (cada uno con su n_clusters optimo)
# ----------------------------------------------------------------------------
# Que se busca: mapear las TRES tipologias resultantes -sin restriccion
# espacial (K_ELEGIDO fijo), la mejor combinacion KNN (su propio n_clusters
# optimo de la seccion 9) y la mejor combinacion DistanceBand (su propio
# n_clusters optimo)- para poder comparar visualmente si la vecindad
# geografica cambia la distribucion espacial de los tipos de altiplano, y si
# el modelo KNN y el modelo DistanceBand llegan a tipologias parecidas o
# distintas entre si.
# ----------------------------------------------------------------------------
gdf["cluster_sin_restriccion"] = etiquetas_base

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 8))

gdf.plot(column="cluster_sin_restriccion", categorical=True, legend=True, cmap="Set2",
         edgecolor="black", linewidth=0.2, ax=ax1)
ax1.set_title(f"Sin restriccion espacial\n(Ward, n_clusters={K_ELEGIDO}, SS={silhouette_base:.3f})")
ax1.set_axis_off()

gdf.plot(column="cluster_mejor_knn", categorical=True, legend=True, cmap="Set2",
         edgecolor="black", linewidth=0.2, ax=ax2)
ax2.set_title(f"Mejor KNN\n(k={mejor_k_knn}, n_clusters={mejor_nclusters_knn}, SS={ss_max_knn:.3f})")
ax2.set_axis_off()

gdf.plot(column="cluster_mejor_distancia", categorical=True, legend=True, cmap="Set2",
         edgecolor="black", linewidth=0.2, ax=ax3)
ax3.set_title(f"Mejor DistanceBand\n(radio={mejor_radio_dist/1000:.1f} km, n_clusters={mejor_nclusters_dist}, SS={ss_max_dist:.3f})")
ax3.set_axis_off()

plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "07_mapa_comparacion_espacial.png"), dpi=150)
plt.show()


# %% [12] EXPORTAR RESULTADOS
# ----------------------------------------------------------------------------
ruta_salida = os.path.join(CARPETA_RESULTADOS, "altiplanos_clustering_espacial.gpkg")
gdf.to_file(ruta_salida, driver="GPKG")
print(f"\nResultado guardado en: {ruta_salida}")

# ============================================================================
# LECTURA DE LOS RESULTADOS:
#   - Si la linea base (sin restriccion espacial) tiene el Silhouette mas
#     alto de las tres configuraciones, significa que para ESTE conjunto de
#     datos la cercania geografica entre altiplanos no ayuda a formar
#     grupos morfometricamente mas compactos; es un resultado legitimo y
#     coherente con que los altiplanos sean "parches" aislados, no un
#     fenomeno regional continuo.
#   - "n_componentes_conectados" alto en DistanceBand para radios pequeños
#     es esperable (muchos altiplanos aislados sin vecinos a esa distancia)
#     y advierte que ese resultado especifico es menos confiable, aunque su
#     Silhouette numerico pudiera verse alto.
# ============================================================================
