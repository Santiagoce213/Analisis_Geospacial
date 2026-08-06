# %% [0] INTRODUCCION
# ============================================================================
# PERFIL DE CLUSTERS CORREGIDO: MEJOR SILHOUETTE PARA n_clusters > 3
# ============================================================================
# Por que existe este script:
#   Complementa a "06_mapas_clusters_n_mayor_3.py". Ese script ya corrige el
#   mapa de la tipologia NO espacial (K-means puro, solo morfometria) usando
#   el mejor Silhouette (SS) con n_clusters > 3 en vez de k=2. Aqui se
#   recalcula la MISMA tipologia (identico k) para regenerar el heatmap de
#   perfil por cluster (analogo a "01_clustering_altiplanos.py" seccion
#   [10], figura "05_heatmap_perfil_clusters.png"), que hasta ahora usaba
#   K_ELEGIDO=4 como valor demostrativo fijo, no el resultado de una busqueda
#   de mejor SS.
#
#   Este script NO modifica "01_clustering_altiplanos.py". El calculo del
#   mejor k (K-means sobre 491 poligonos, barrido k=2..50) es rapido y se
#   repite aqui de forma independiente para no depender de que el barrido
#   espacial (mucho mas lento) de "06_mapas_clusters_n_mayor_3.py" haya
#   terminado. Las figuras se exportan SOLO a "Imagenes".
# ============================================================================

import struct
import os

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

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


# %% [2] CARGA DE DATOS Y VARIABLES (identico a 01)
gdf = gpd.read_file(RUTA_SHP)
gdf.columns = nombres_reales_columnas_dbf(RUTA_DBF) + ["geometry"]

variables_cluster = [
    "Altitud_X", "Altitud_St", "Alt_90", "Alt_50", "Alt_10",
    "Relieve_X", "Relieve_St", "Pend_X", "Pend_St",
]

escalador = StandardScaler()
X = escalador.fit_transform(gdf[variables_cluster])

print(f"Poligonos cargados: {len(gdf)}")


# %% [3] MEJOR K-MEANS CON n_clusters > 3 SEGUN SS (mismo criterio que 06)
rango_k = range(2, 51)
siluetas = []
for k in rango_k:
    modelo_k = KMeans(n_clusters=k, random_state=SEMILLA, n_init=10)
    etiquetas_k = modelo_k.fit_predict(X)
    siluetas.append(silhouette_score(X, etiquetas_k))

rango_k = list(rango_k)
candidatos_validos = [(k, ss) for k, ss in zip(rango_k, siluetas) if k >= N_CLUSTERS_MINIMO]
mejor_k, mejor_ss = max(candidatos_validos, key=lambda par: par[1])

print(f"\nMejor k por SS con k>=4: k={mejor_k} (SS={mejor_ss:.3f})")

modelo_kmeans = KMeans(n_clusters=mejor_k, random_state=SEMILLA, n_init=10)
gdf["cluster_kmeans_n_mayor_3"] = modelo_kmeans.fit_predict(X)

print("\nNumero de altiplanos por cluster:")
print(gdf["cluster_kmeans_n_mayor_3"].value_counts().sort_index())


# %% [4] MAPA NO ESPACIAL CORREGIDO (solo morfometria, sin restriccion espacial)
# ----------------------------------------------------------------------------
# Analogo a "01_clustering_altiplanos.py" seccion [9] ("04_mapa_clusters.png"),
# usando el nuevo mejor_k (n_clusters > 3) en vez de K_ELEGIDO=4 fijo.
# ----------------------------------------------------------------------------
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
ax.set_title(f"Tipologia de altiplanos - K-means (solo morfometria, sin restriccion espacial)\n"
             f"Mejor SS con n_clusters > 3: k={mejor_k} (SS={mejor_ss:.3f})")
ax.set_axis_off()
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_IMAGENES, "04_mapa_clusters_n_mayor_3.png"), dpi=150)
plt.show()


# %% [5] HEATMAP DE PERFIL POR CLUSTER (CORREGIDO)
# ----------------------------------------------------------------------------
# Analogo a "01_clustering_altiplanos.py" seccion [10]
# ("05_heatmap_perfil_clusters.png"), pero calculado sobre la tipologia con
# el nuevo mejor_k (n_clusters > 3) en vez de K_ELEGIDO=4 fijo.
# ----------------------------------------------------------------------------
perfil_clusters = gdf.groupby("cluster_kmeans_n_mayor_3")[variables_cluster].mean()
print("\nPerfil promedio por cluster:")
print(perfil_clusters)

perfil_normalizado = (perfil_clusters - perfil_clusters.mean()) / perfil_clusters.std()

plt.figure(figsize=(8, 4 + 0.15 * max(0, mejor_k - 4)))
sns.heatmap(perfil_normalizado.T, annot=perfil_clusters.T, fmt=".1f", cmap="RdBu_r", center=0)
plt.title(f"Perfil de cada cluster (color = z-score, numero = valor real)\n"
          f"Mejor SS con n_clusters > 3: k={mejor_k} (SS={mejor_ss:.3f})")
plt.xlabel("Cluster")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_IMAGENES, "05_heatmap_perfil_clusters_n_mayor_3.png"), dpi=150)
plt.show()

composicion_geologia = pd.crosstab(gdf["cluster_kmeans_n_mayor_3"], gdf["Geología"], normalize="index") * 100
print("\nComposicion litologica por cluster (% de poligonos):")
print(composicion_geologia.round(1))

print("\nFiguras corregidas guardadas en Imagenes:")
print(" - 04_mapa_clusters_n_mayor_3.png")
print(" - 05_heatmap_perfil_clusters_n_mayor_3.png")
