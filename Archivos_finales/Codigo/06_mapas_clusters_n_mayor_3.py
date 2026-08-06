# %% [0] INTRODUCCION
# ============================================================================
# MAPAS DE CLUSTERS CORREGIDOS: MEJOR SILHOUETTE PARA n_clusters > 3
# ============================================================================
# Por que existe este script:
#   En "01_clustering_altiplanos.py" y "02_clustering_espacial_altiplanos.py"
#   se encontro que el Silhouette (SS) es maximo globalmente en k=2 (tanto
#   para K-means no espacial como para KNN/DistanceBand espacial). Por
#   instruccion explicita del usuario, k=2 no tiene sentido geomorfologico
#   suficiente para este trabajo, asi que aqui se repite la busqueda del
#   MEJOR SS pero restringida a n_clusters > 3 (minimo 4 grupos), tanto para
#   el clustering NO espacial (K-means) como para el espacial (KNN y
#   DistanceBand).
#
#   Este script NO modifica "01_clustering_altiplanos.py" ni
#   "02_clustering_espacial_altiplanos.py"; reproduce el mismo pipeline de
#   datos y los mismos metodos (misma SEMILLA=42, mismas 9 variables
#   estandarizadas, mismas vecindades candidatas) unicamente para regenerar
#   los mapas de clusters con el nuevo criterio de seleccion de k, y exporta
#   las figuras SOLO a la carpeta "Imagenes" (las figuras originales en
#   "Resultados" quedan intactas).
# ============================================================================

import struct
import os
import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, calinski_harabasz_score

from libpysal.weights import KNN, DistanceBand

RUTA_SHP = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Capas\Estadisticas_Cluster.shp"
RUTA_DBF = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Capas\Estadisticas_Cluster.dbf"
CARPETA_IMAGENES = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Imagenes"

SEMILLA = 42
N_CLUSTERS_MINIMO = 4  # se descartan k=2 y k=3 al buscar el mejor SS


# %% [1] UTILIDAD: CORRECCION DE CODIFICACION DEL DBF (identica a 01/02)
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


# %% [2] CARGA DE DATOS Y VARIABLES (identico a 01/02)
gdf = gpd.read_file(RUTA_SHP)
gdf.columns = nombres_reales_columnas_dbf(RUTA_DBF) + ["geometry"]

variables_cluster = [
    "Altitud_X", "Altitud_St", "Alt_90", "Alt_50", "Alt_10",
    "Relieve_X", "Relieve_St", "Pend_X", "Pend_St",
]

escalador = StandardScaler()
X = escalador.fit_transform(gdf[variables_cluster])

print(f"Poligonos cargados: {len(gdf)}")


# %% [3] NO ESPACIAL: MEJOR K-MEANS CON n_clusters > 3 SEGUN SS
# ----------------------------------------------------------------------------
# Mismo barrido k=2..50 de "01_clustering_altiplanos.py" seccion [6], pero
# esta vez se busca el argmax de Silhouette SOLO entre k=4..50 (se descartan
# k=2 y k=3 antes de tomar el maximo, no despues).
# ----------------------------------------------------------------------------
rango_k = range(2, 51)
siluetas_kmeans = []
for k in rango_k:
    modelo_k = KMeans(n_clusters=k, random_state=SEMILLA, n_init=10)
    etiquetas_k = modelo_k.fit_predict(X)
    siluetas_kmeans.append(silhouette_score(X, etiquetas_k))

rango_k = list(rango_k)
candidatos_validos = [(k, ss) for k, ss in zip(rango_k, siluetas_kmeans) if k >= N_CLUSTERS_MINIMO]
mejor_k_no_espacial, mejor_ss_no_espacial = max(candidatos_validos, key=lambda par: par[1])

print(f"\n[No espacial] Mejor k por SS con k>=4: k={mejor_k_no_espacial} (SS={mejor_ss_no_espacial:.3f})")
print(f"[No espacial] (referencia) mejor k por SS sin restriccion: "
      f"k={rango_k[int(np.argmax(siluetas_kmeans))]} (SS={max(siluetas_kmeans):.3f})")

modelo_kmeans_final = KMeans(n_clusters=mejor_k_no_espacial, random_state=SEMILLA, n_init=10)
gdf["cluster_kmeans_n_mayor_3"] = modelo_kmeans_final.fit_predict(X)

fig, ax = plt.subplots(1, figsize=(9, 9))
gdf.plot(
    column="cluster_kmeans_n_mayor_3",
    categorical=True,
    legend=True,
    cmap="Set2",
    edgecolor="black",
    linewidth=0.3,
    ax=ax,
)
ax.set_title(
    f"Tipologia de altiplanos - K-means\n"
    f"Mejor SS con n_clusters > 3: k={mejor_k_no_espacial} (SS={mejor_ss_no_espacial:.3f})"
)
ax.set_axis_off()
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_IMAGENES, "04_mapa_clusters_n_mayor_3.png"), dpi=150)
plt.show()


# %% [4] ESPACIAL: BARRIDO KNN/DISTANCEBAND x n_clusters (identico a 02, seccion 8)
def simetrizar(matriz_dispersa):
    return matriz_dispersa.maximum(matriz_dispersa.T)


def cortar_arbol_aglomerativo(children, n_muestras, n_clusters):
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

    n_fusiones = n_muestras - n_clusters
    for i in range(n_fusiones):
        a, b = int(children[i, 0]), int(children[i, 1])
        unir(a, b)
        unir(a, n_muestras + i)

    raices = np.array([encontrar(j) for j in range(n_muestras)])
    _, etiquetas = np.unique(raices, return_inverse=True)
    return etiquetas


def barrido_metricas_2d(valores_vecindad, construir_pesos, rango_n_clusters, X):
    n_muestras = X.shape[0]
    matriz_ss = np.full((len(valores_vecindad), len(rango_n_clusters)), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i, valor_vecindad in enumerate(valores_vecindad):
            try:
                conectividad = simetrizar(construir_pesos(valor_vecindad).sparse)
                modelo = AgglomerativeClustering(
                    n_clusters=2, linkage="ward", connectivity=conectividad, compute_full_tree=True
                ).fit(X)
            except Exception:
                continue
            for j, n_clusters in enumerate(rango_n_clusters):
                try:
                    etiquetas = cortar_arbol_aglomerativo(modelo.children_, n_muestras, n_clusters)
                    if len(np.unique(etiquetas)) < 2:
                        continue
                    matriz_ss[i, j] = silhouette_score(X, etiquetas)
                except Exception:
                    continue
    return matriz_ss


centroides = gdf.geometry.centroid
coordenadas = np.column_stack([centroides.x, centroides.y])
arbol = cKDTree(coordenadas)
distancias, _ = arbol.query(coordenadas, k=2)
distancia_vecino_mas_cercano = distancias[:, 1]

radios_candidatos = sorted(set(
    int(round(v, -2)) for v in np.percentile(distancia_vecino_mas_cercano, [50, 60, 70, 80, 90, 95, 99, 100])
))
vecinos_candidatos = [3, 4, 5, 6, 8, 10, 15, 20, 30, 40]
rango_n_clusters = list(range(2, 51))

matriz_ss_knn = barrido_metricas_2d(
    vecinos_candidatos, lambda k: KNN.from_dataframe(gdf, k=k), rango_n_clusters, X
)
matriz_ss_distancia = barrido_metricas_2d(
    radios_candidatos, lambda d: DistanceBand.from_dataframe(gdf, threshold=d, binary=True), rango_n_clusters, X
)

print("\nBarrido espacial completado.")


# %% [5] MEJOR (VECINDAD, N_CLUSTERS) CON n_clusters > 3 (KNN y DistanceBand)
# ----------------------------------------------------------------------------
# Igual que "02_clustering_espacial_altiplanos.py" seccion [9], pero el
# argmax se toma solo sobre las columnas de la grilla con n_clusters >= 4
# (se descartan las columnas de n_clusters=2 y 3 ANTES de buscar el maximo).
# ----------------------------------------------------------------------------
idx_col_validas = [j for j, n in enumerate(rango_n_clusters) if n >= N_CLUSTERS_MINIMO]


def mejor_combinacion_restringida(matriz, valores_vecindad, rango_n_clusters, columnas_validas):
    sub_matriz = matriz[:, columnas_validas]
    if np.all(np.isnan(sub_matriz)):
        return None, None, np.nan
    idx_plano = np.nanargmax(sub_matriz)
    i, j_sub = np.unravel_index(idx_plano, sub_matriz.shape)
    j = columnas_validas[j_sub]
    return valores_vecindad[i], rango_n_clusters[j], sub_matriz[i, j_sub]


mejor_k_knn, mejor_nclusters_knn, ss_max_knn = mejor_combinacion_restringida(
    matriz_ss_knn, vecinos_candidatos, rango_n_clusters, idx_col_validas
)
mejor_radio_dist, mejor_nclusters_dist, ss_max_dist = mejor_combinacion_restringida(
    matriz_ss_distancia, radios_candidatos, rango_n_clusters, idx_col_validas
)

print(f"\n[KNN] Mejor combinacion con n_clusters>=4 segun SS: "
      f"k={mejor_k_knn}, n_clusters={mejor_nclusters_knn} (SS={ss_max_knn:.3f})")
print(f"[DistanceBand] Mejor combinacion con n_clusters>=4 segun SS: "
      f"radio={mejor_radio_dist/1000:.1f} km, n_clusters={mejor_nclusters_dist} (SS={ss_max_dist:.3f})")

w_ganador_knn = KNN.from_dataframe(gdf, k=mejor_k_knn)
conectividad_ganadora_knn = simetrizar(w_ganador_knn.sparse)
n_componentes_knn, _ = connected_components(conectividad_ganadora_knn, directed=False)
etiquetas_mejor_knn = AgglomerativeClustering(
    n_clusters=mejor_nclusters_knn, linkage="ward", connectivity=conectividad_ganadora_knn
).fit_predict(X)

w_ganador_dist = DistanceBand.from_dataframe(gdf, threshold=mejor_radio_dist, binary=True)
conectividad_ganadora_dist = simetrizar(w_ganador_dist.sparse)
n_componentes_dist, _ = connected_components(conectividad_ganadora_dist, directed=False)
etiquetas_mejor_dist = AgglomerativeClustering(
    n_clusters=mejor_nclusters_dist, linkage="ward", connectivity=conectividad_ganadora_dist
).fit_predict(X)

print(f"[KNN] Componentes conectados con k={mejor_k_knn}: {n_componentes_knn}")
print(f"[DistanceBand] Componentes conectados con radio={mejor_radio_dist/1000:.1f} km: {n_componentes_dist}")

gdf["cluster_mejor_knn_n_mayor_3"] = etiquetas_mejor_knn
gdf["cluster_mejor_distancia_n_mayor_3"] = etiquetas_mejor_dist
gdf["cluster_sin_restriccion_n_mayor_3"] = gdf["cluster_kmeans_n_mayor_3"]  # misma referencia no espacial de la seccion 3


# %% [6] MAPA COMPARATIVO CORREGIDO: SIN RESTRICCION, MEJOR KNN, MEJOR DISTANCEBAND
# ----------------------------------------------------------------------------
# Analogo a "02_clustering_espacial_altiplanos.py" seccion [11]
# ("07_mapa_comparacion_espacial.png"), pero con el nuevo criterio de
# seleccion (mejor SS con n_clusters > 3) en los tres paneles.
# ----------------------------------------------------------------------------
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 8))

gdf.plot(column="cluster_sin_restriccion_n_mayor_3", categorical=True, legend=True, cmap="Set2",
         edgecolor="black", linewidth=0.2, ax=ax1)
ax1.set_title(f"Sin restriccion espacial (K-means)\nn_clusters={mejor_k_no_espacial}, SS={mejor_ss_no_espacial:.3f}")
ax1.set_axis_off()

gdf.plot(column="cluster_mejor_knn_n_mayor_3", categorical=True, legend=True, cmap="Set2",
         edgecolor="black", linewidth=0.2, ax=ax2)
ax2.set_title(f"Mejor KNN (n_clusters>3)\nk={mejor_k_knn}, n_clusters={mejor_nclusters_knn}, SS={ss_max_knn:.3f}")
ax2.set_axis_off()

gdf.plot(column="cluster_mejor_distancia_n_mayor_3", categorical=True, legend=True, cmap="Set2",
         edgecolor="black", linewidth=0.2, ax=ax3)
ax3.set_title(f"Mejor DistanceBand (n_clusters>3)\nradio={mejor_radio_dist/1000:.1f} km, "
              f"n_clusters={mejor_nclusters_dist}, SS={ss_max_dist:.3f}")
ax3.set_axis_off()

fig.suptitle("Mapas de clusters corregidos: mejor Silhouette exigiendo n_clusters > 3", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_IMAGENES, "07_mapa_comparacion_espacial_n_mayor_3.png"), dpi=150)
plt.show()

print("\nFiguras corregidas guardadas en Imagenes:")
print(" - 04_mapa_clusters_n_mayor_3.png")
print(" - 07_mapa_comparacion_espacial_n_mayor_3.png")
