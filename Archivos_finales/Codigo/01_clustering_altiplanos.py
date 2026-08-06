# %% [0] INTRODUCCION
# ============================================================================
# ANALISIS DE CLASIFICACION POR CLUSTERING - ALTIPLANOS
# ============================================================================
# Que se busca:
#   Se cuenta con 491 poligonos delimitados manualmente, cada uno identificado
#   previamente como "altiplano" a partir de criterios de relieve relativo,
#   pendiente y altitud. Estos poligonos NO son contiguos entre si (no
#   comparten borde ni se tocan), por lo que no representan un mosaico
#   continuo del territorio sino "parches" aislados de superficie de
#   aplanamiento.
#
#   El objetivo de este script es CLASIFICAR (tipificar) esos 491 altiplanos
#   en grupos morfometricos homogeneos, es decir, responder: ?existen
#   "tipos" de altiplano (p.ej. altos y escarpados vs. bajos y suaves) y
#   cuales subcuencas/poligonos pertenecen a cada tipo?
#
# Metodo del libro utilizado:
#   Notebook "08_ClusterEspacial" del libro Analisis Geoespacial (Aristizabal).
#   Como los poligonos NO son contiguos, la matriz de pesos espaciales tipo
#   Queen/Rook no es aplicable (cada poligono aislado quedaria como "isla"
#   sin vecinos). Por esta razon NO se usa la variante de "regionalizacion"
#   con restriccion espacial que propone el libro (esa tecnica sirve para
#   FUSIONAR unidades vecinas en regiones contiguas, lo cual no aplica aqui
#   porque los altiplanos ya fueron delimitados a mano y no se busca
#   fusionarlos). En su lugar se usa la parte NO espacial del mismo notebook:
#   clustering de atributos con K-means y clustering jerarquico (Ward),
#   tratando cada altiplano como una observacion multivariada descrita por
#   su perfil de altitud, relieve y pendiente.
#
# Ventajas / desventajas generales de este enfoque (clustering de atributos
# vs. regionalizacion espacial):
#   (+) Es el metodo correcto cuando las unidades no tienen una relacion de
#       vecindad geografica real que deba respetarse.
#   (+) Permite encontrar similitudes morfometricas entre altiplanos muy
#       alejados entre si (p.ej. uno en el norte y otro en el sur pueden
#       ser del mismo "tipo").
#   (-) Ignora por completo la ubicacion geografica: dos altiplanos del
#       mismo tipo podrian estar en extremos opuestos del area de estudio,
#       y esta tecnica no lo señala como relevante ni irrelevante.
# ============================================================================

import struct
import os

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from scipy.cluster.hierarchy import dendrogram, linkage
from tslearn.clustering import TimeSeriesKMeans

# Configuracion general de rutas del proyecto
RUTA_SHP = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Capas\Estadisticas_Cluster.shp"
RUTA_DBF = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Capas\Estadisticas_Cluster.dbf"
CARPETA_RESULTADOS = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Resultados"

SEMILLA = 42  # fija la aleatoriedad para que los resultados sean reproducibles


# %% [1] UTILIDAD: CORRECCION DE CODIFICACION DEL DBF
# ----------------------------------------------------------------------------
# Que se busca:
#   El archivo .dbf de este shapefile tiene un defecto conocido de ArcGIS/GDAL:
#   el .cpg declara UTF-8, y los VALORES de texto (p.ej. "Geologia") se leen
#   bien con ese encoding, pero pyogrio/GDAL no aplica el encoding declarado
#   a los NOMBRES DE COLUMNA, por lo que columnas como "Geolog{i}a" o "{A}rea"
#   llegan corruptas (con caracteres de reemplazo). Verificado leyendo los
#   bytes crudos del encabezado del .dbf: son UTF-8 valido, asi que basta con
#   leer el nombre de cada campo directamente del encabezado binario del
#   archivo y renombrar las columnas del GeoDataFrame.
# ----------------------------------------------------------------------------
def nombres_reales_columnas_dbf(ruta_dbf: str, encoding: str = "utf-8") -> list[str]:
    """Lee los nombres de campo directamente del encabezado binario del .dbf.

    Esto evita el error de decodificacion que pyogrio/GDAL introduce en los
    nombres de columna (no en los valores) de archivos .dbf con acentos.
    """
    with open(ruta_dbf, "rb") as f:
        encabezado = f.read(32)
        tam_encabezado = struct.unpack("<H", encabezado[8:10])[0]
        f.seek(0)
        encabezado_completo = f.read(tam_encabezado)

    nombres = []
    offset = 32
    while True:
        descriptor = encabezado_completo[offset:offset + 32]
        # 0x0D marca el fin de la lista de campos
        if descriptor[0:1] == b"\x0d" or len(descriptor) < 32:
            break
        crudo = descriptor[0:11].split(b"\x00")[0]
        nombres.append(crudo.decode(encoding))
        offset += 32
    return nombres


# %% [2] CARGA DE DATOS
# ----------------------------------------------------------------------------
# Que se busca: cargar el shapefile como GeoDataFrame y corregir los nombres
# de columna con la utilidad anterior.
# ----------------------------------------------------------------------------
gdf = gpd.read_file(RUTA_SHP)

nombres_corregidos = nombres_reales_columnas_dbf(RUTA_DBF) + ["geometry"]
assert len(nombres_corregidos) == len(gdf.columns), (
    "El numero de nombres leidos del .dbf no coincide con el numero de "
    "columnas del GeoDataFrame; revisar manualmente antes de continuar."
)
gdf.columns = nombres_corregidos

print(f"Poligonos cargados: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print(f"Columnas: {list(gdf.columns)}")


# %% [3] EXPLORACION INICIAL
# ----------------------------------------------------------------------------
# Que se busca: revisar valores nulos, duplicados y la distribucion basica
# de las variables antes de meterlas a un algoritmo de clustering. Esto
# corresponde al primer paso de cualquier analisis de datos de area del
# libro (notebook "00_Data" / "01_DatosEspaciales"): nunca modelar sin
# antes conocer la calidad y forma de los datos.
# ----------------------------------------------------------------------------
print("\nValores nulos por columna:")
print(gdf.isna().sum()[gdf.isna().sum() > 0])

print("\nDistribucion de la variable categorica Geologia:")
print(gdf["Geología"].value_counts())

print("\nEstadisticos descriptivos de las variables morfometricas:")
variables_resumen = ["Altitud_X", "Altitud_St", "Alt_90", "Alt_50", "Alt_10", "Relieve_X", "Relieve_St", "Pend_X", "Pend_St"]
print(gdf[variables_resumen].describe().T)


# %% [4] SELECCION DE VARIABLES Y ESTANDARIZACION
# ----------------------------------------------------------------------------
# Que se busca:
#   Elegir el perfil morfometrico que describe a cada altiplano. Se usan las
#   6 variables de media y desviacion estandar de altitud, relieve y
#   pendiente, MAS los tres percentiles de altitud (Alt_90, Alt_50, Alt_10)
#   que ya trae la tabla de datos. Estos percentiles no son redundantes con
#   Altitud_X/Altitud_St: la media y la desviacion estandar resumen la
#   distribucion de altitud dentro del poligono asumiendo (implicitamente)
#   una forma aproximadamente simetrica, mientras que los percentiles
#   permiten distinguir altiplanos con una distribucion de altitud sesgada
#   (p.ej. un poligono con una "cola" de terreno alto minoritario) de otro
#   con una distribucion simetrica, aunque ambos compartan la misma media y
#   desviacion estandar. No se agregaron los percentiles de Relieve o
#   Pendiente (Rel_90/50/10, Slp_90/50/10) para mantener el numero de
#   variables manejable; ver el paso [5] de correlacion para confirmar que
#   los percentiles de altitud aportan informacion no totalmente redundante.
#   El area no se incluye porque es una medida de TAMAÑO del poligono
#   (depende de como se digitalizo a mano), no de su morfometria interna, y
#   la variable Geologia se deja fuera por ser categorica (K-means solo
#   trabaja con distancia euclidiana sobre variables continuas).
#
# Metodo del libro utilizado:
#   Igual que en "08_ClusterEspacial", se estandarizan las variables con
#   StandardScaler ANTES de aplicar el algoritmo. Esto es indispensable
#   porque Altitud esta en metros (cientos-miles), Relieve en metros
#   (decenas) y Pendiente en grados (unidades): sin estandarizar, la
#   Altitud dominaria por completo la distancia euclidiana y el
#   agrupamiento resultante solo reflejaria diferencias de altura.
#
# Ventajas / desventajas de estandarizar con media=0 y desv.=1:
#   (+) Pone a las tres variables en pie de igualdad para el calculo de
#       distancias.
#   (-) Es sensible a valores atipicos extremos (un outlier infla la
#       desviacion estandar y "comprime" al resto de las observaciones).
#       Con datos muy sesgados a veces conviene usar RobustScaler en su
#       lugar; aqui se usa StandardScaler por ser el estandar del libro y
#       porque los datos no muestran outliers extremos (ver paso 3).
# ----------------------------------------------------------------------------
variables_cluster = [
    "Altitud_X", "Altitud_St", "Alt_90", "Alt_50", "Alt_10",
    "Relieve_X", "Relieve_St", "Pend_X", "Pend_St",
]

escalador = StandardScaler()
X_estandarizado = escalador.fit_transform(gdf[variables_cluster])
X_estandarizado_df = pd.DataFrame(X_estandarizado, columns=variables_cluster, index=gdf.index)


# %% [5] CORRELACION ENTRE VARIABLES (chequeo previo)
# ----------------------------------------------------------------------------
# Que se busca: verificar que no haya variables casi perfectamente
# redundantes (p.ej. correlacion > 0.95) antes de agruparlas, ya que dos
# variables muy correlacionadas pesarian el doble en la distancia
# euclidiana sin aportar informacion nueva.
# ----------------------------------------------------------------------------
correlacion = gdf[variables_cluster].corr()

plt.figure(figsize=(6, 5))
sns.heatmap(correlacion, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1)
plt.title("Correlacion entre variables morfometricas")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "01_correlacion_variables.png"), dpi=150)
plt.show()


# %% [6] NUMERO OPTIMO DE CLUSTERS: CODO, SILHOUETTE Y CALINSKI-HARABASZ
# ----------------------------------------------------------------------------
# Que se busca: K-means exige fijar de antemano el numero de grupos (k).
# Para elegirlo de forma informada se prueban varios valores de k y se
# comparan TRES criterios (no solo dos): al Silhouette se agrega el indice
# de Calinski-Harabasz como una segunda condicion/criterio de validacion de
# clusters, independiente del Silhouette.
#
# Metodo del libro utilizado:
#   Igual que en la Actividad 1 de "08_ClusterEspacial": se calcula la
#   inercia (suma de distancias al cuadrado dentro de cada cluster) para el
#   metodo del codo, y el coeficiente de Silhouette para cada k. El indice
#   de Calinski-Harabasz (tambien llamado "Variance Ratio Criterion") no
#   viene del libro, sino de pruebas previas de este mismo proyecto.
#
# Ventajas / desventajas de cada criterio:
#   Metodo del codo (inercia):
#     (+) Facil de calcular e interpretar visualmente.
#     (-) Subjetivo: el "codo" no siempre es un quiebre claro en la curva,
#         distintas personas pueden leer distintos k en el mismo grafico.
#   Coeficiente de Silhouette:
#     (+) Da un numero objetivo entre -1 y 1 que puede compararse
#         directamente entre distintos valores de k (mas alto = clusters
#         mejor separados y mas compactos).
#     (-) Mas costoso computacionalmente (compara cada punto contra todos
#         los demas, O(n^2)) y tiende a favorecer clusters de forma convexa
#         y tamaño similar, penalizando estructuras alargadas o irregulares
#         aunque sean geomorficamente validas.
#   Indice de Calinski-Harabasz:
#     (+) Mucho mas barato de calcular que el Silhouette (se basa en la
#         dispersion entre-grupos vs. dentro-de-grupos, O(n) en la practica),
#         por lo que es util cuando se quiere evaluar muchisimas
#         combinaciones de parametros (ver seccion [8] del script
#         "02_clustering_espacial_altiplanos.py").
#     (-) No tiene un rango fijo (no va de -1 a 1 ni de 0 a 1): solo sirve
#         para COMPARAR configuraciones entre si (mayor es mejor), no para
#         juzgar de forma absoluta que tan buena es una particion.
#     (-) Al igual que el Silhouette, tiende a favorecer clusters convexos y
#         de varianza similar, y ademas tiende a preferir MENOS clusters
#         (valores de k pequeños), por lo que rara vez coincide exactamente
#         con el optimo del Silhouette; se reporta aqui como una segunda
#         opinion, no como reemplazo.
# ----------------------------------------------------------------------------
# Rango ampliado a 2-50 clusters (antes 2-10) para explorar el comportamiento
# del codo, el Silhouette y Calinski-Harabasz en un rango mucho mas amplio de
# granularidad.
# Nota de interpretacion: con solo 491 poligonos, valores de k cercanos a 50
# implican grupos de menos de 10 altiplanos en promedio; mas alla de cierto
# punto los "clusters" dejan de representar tipos geomorfologicos genuinos y
# empiezan a idiosincraticamente aislar observaciones individuales, asi que
# un Silhouette (o Calinski-Harabasz) alto en la zona de k grandes no
# necesariamente es deseable.
rango_k = range(2, 51)
inercias = []
siluetas = []
calinski_harabasz = []

for k in rango_k:
    modelo_k = KMeans(n_clusters=k, random_state=SEMILLA, n_init=10)
    etiquetas_k = modelo_k.fit_predict(X_estandarizado)
    inercias.append(modelo_k.inertia_)
    siluetas.append(silhouette_score(X_estandarizado, etiquetas_k))
    calinski_harabasz.append(calinski_harabasz_score(X_estandarizado, etiquetas_k))

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 4.5))

ax1.plot(list(rango_k), inercias, marker="o", markersize=3)
ax1.set_xlabel("Numero de clusters (k)")
ax1.set_ylabel("Inercia (suma de distancias^2)")
ax1.set_title("Metodo del codo")
ax1.set_xticks(list(range(2, 51, 4)))

ax2.plot(list(rango_k), siluetas, marker="o", markersize=3, color="darkorange")
ax2.set_xlabel("Numero de clusters (k)")
ax2.set_ylabel("Coeficiente de Silhouette")
ax2.set_title("Silhouette por numero de clusters")
ax2.set_xticks(list(range(2, 51, 4)))

ax3.plot(list(rango_k), calinski_harabasz, marker="o", markersize=3, color="seagreen")
ax3.set_xlabel("Numero de clusters (k)")
ax3.set_ylabel("Indice de Calinski-Harabasz")
ax3.set_title("Calinski-Harabasz por numero de clusters")
ax3.set_xticks(list(range(2, 51, 4)))

plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "02_seleccion_k.png"), dpi=150)
plt.show()

print("\nInercia, Silhouette y Calinski-Harabasz por k:")
for k, inercia, silueta, ch in zip(rango_k, inercias, siluetas, calinski_harabasz):
    print(f"  k={k}: inercia={inercia:.1f}  silhouette={silueta:.3f}  calinski_harabasz={ch:.1f}")

mejor_k_silhouette = list(rango_k)[int(np.argmax(siluetas))]
mejor_k_ch = list(rango_k)[int(np.argmax(calinski_harabasz))]
print(f"\nMejor k segun Silhouette: {mejor_k_silhouette}  |  Mejor k segun Calinski-Harabasz: {mejor_k_ch}")

# IMPORTANTE: inspeccionar los dos graficos impresos arriba y decidir el
# valor de K_ELEGIDO a mano antes de continuar. No se automatiza la
# eleccion porque el "codo" y el maximo de Silhouette pueden no coincidir,
# y la decision final debe considerar tambien si los grupos resultantes
# tienen sentido geomorfologico (paso 9).
K_ELEGIDO = 4  # <-- AJUSTAR segun los graficos generados arriba


# %% [7] CLUSTERING K-MEANS (MODELO FINAL)
# ----------------------------------------------------------------------------
# Que se busca: asignar a cada uno de los 491 altiplanos una etiqueta de
# grupo (0, 1, 2, ...) segun su perfil morfometrico estandarizado.
#
# Metodo del libro utilizado: K-means de "08_ClusterEspacial"
# (sklearn.cluster.KMeans), igual que en el ejemplo del libro con el
# dataset de cuencas colombianas.
#
# Ventajas / desventajas de K-means en general:
#   (+) Simple, rapido y escalable incluso con miles de observaciones.
#   (+) Facil de interpretar: cada cluster queda representado por su
#       centroide (el "perfil promedio" del grupo).
#   (-) Asume que los grupos son razonablemente esfericos y de tamaño
#       similar en el espacio estandarizado; si los tipos reales de
#       altiplano tienen formas muy distintas de dispersion, K-means puede
#       partirlos de forma poco natural.
#   (-) El resultado depende de la inicializacion aleatoria de los
#       centroides (mitigado aqui con n_init=10, que prueba 10
#       inicializaciones y se queda con la mejor) y puede converger a un
#       minimo local, no necesariamente al optimo global.
#   (-) No maneja directamente variables categoricas (por eso Geologia
#       quedo fuera del paso 4; se usa solo para interpretar los grupos ya
#       formados, ver paso 9).
# ----------------------------------------------------------------------------
modelo_kmeans = KMeans(n_clusters=K_ELEGIDO, random_state=SEMILLA, n_init=10)
gdf["cluster_kmeans"] = modelo_kmeans.fit_predict(X_estandarizado)

print("\nNumero de altiplanos por cluster (K-means):")
print(gdf["cluster_kmeans"].value_counts().sort_index())


# %% [8] CLUSTERING JERARQUICO (WARD) COMO CONTRASTE
# ----------------------------------------------------------------------------
# Que se busca: comparar el resultado de K-means con un metodo alternativo
# que no depende de una inicializacion aleatoria ni de fijar k desde el
# principio, para verificar que la tipologia encontrada es robusta y no un
# artefacto de un solo algoritmo.
#
# Metodo del libro utilizado:
#   Igual que en "08_ClusterEspacial": union aglomerativa con criterio de
#   Ward (minimiza el incremento de varianza dentro de cada grupo al
#   fusionar), construyendo el dendrograma con
#   scipy.cluster.hierarchy.linkage/dendrogram.
#
# Ventajas / desventajas del clustering jerarquico (Ward):
#   (+) No requiere decidir k de antemano: el dendrograma se puede "cortar"
#       a distintas alturas para explorar distintas resoluciones (2
#       grupos, 4 grupos, 8 grupos, etc.) sin recalcular nada.
#   (+) Es determinista (no depende de una semilla aleatoria como K-means).
#   (-) Computacionalmente mas costoso: compara todas las observaciones
#       entre si en cada paso de fusion (O(n^2) en memoria y tiempo), lo
#       que lo hace poco practico para decenas de miles de observaciones
#       (con 491 poligonos no es un problema).
#   (-) Una vez que dos observaciones se fusionan, la decision es
#       irreversible (no puede "deshacerse" mas adelante en el algoritmo),
#       a diferencia de K-means que reasigna observaciones en cada
#       iteracion.
# ----------------------------------------------------------------------------
matriz_enlace = linkage(X_estandarizado, method="ward", metric="euclidean")

plt.figure(figsize=(10, 4))
dendrogram(
    matriz_enlace,
    truncate_mode="lastp",
    p=30,
    leaf_rotation=90.0,
    leaf_font_size=8,
    show_leaf_counts=True,
    show_contracted=True,
)
plt.xlabel("Altiplanos agrupados (o su indice)")
plt.ylabel("Distancia de union (Ward)")
plt.title("Dendrograma - clustering jerarquico de altiplanos")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "03_dendrograma.png"), dpi=150)
plt.show()

# Se corta el dendrograma en el mismo numero de grupos elegido para K-means,
# para poder comparar ambas soluciones directamente.
modelo_ward = AgglomerativeClustering(n_clusters=K_ELEGIDO, linkage="ward")
gdf["cluster_ward"] = modelo_ward.fit_predict(X_estandarizado)

# Tabla de contingencia: ?que tanto coinciden K-means y Ward?
tabla_comparacion = pd.crosstab(gdf["cluster_kmeans"], gdf["cluster_ward"])
print("\nTabla de contingencia K-means (filas) vs. Ward (columnas):")
print(tabla_comparacion)


# %% [9] MAPA DE LOS CLUSTERS
# ----------------------------------------------------------------------------
# Que se busca: visualizar donde se ubica cada tipo de altiplano en el
# territorio. Aunque el clustering no usa la ubicacion geografica como
# variable, mapear el resultado permite ver si los tipos morfometricos
# tienen ademas algun patron espacial (p.ej. un tipo concentrado en el
# norte), lo cual seria una pregunta natural para explorar mas adelante
# con autocorrelacion espacial (notebook "07_MatrizCorrelacion").
#
# Metodo del libro utilizado: mapa categorico con geopandas, igual que en
# "08_ClusterEspacial" (gdf.plot(column=..., categorical=True)).
# ----------------------------------------------------------------------------
fig, ax = plt.subplots(1, figsize=(9, 9))
gdf.plot(
    column="cluster_kmeans",
    categorical=True,
    legend=True,
    cmap="Set2",
    edgecolor="black",
    linewidth=0.3,
    ax=ax,
)
ax.set_title(f"Tipologia de altiplanos - K-means (k={K_ELEGIDO})")
ax.set_axis_off()
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "04_mapa_clusters.png"), dpi=150)
plt.show()


# %% [10] PERFILAMIENTO DE LOS CLUSTERS (interpretacion)
# ----------------------------------------------------------------------------
# Que se busca: los clusters solo son numeros (0, 1, 2...) hasta que se les
# da un nombre geomorfologico. Este paso calcula el perfil promedio de cada
# grupo y su distribucion de litologia dominante, para poder describirlos
# en palabras (p.ej. "Cluster 2: altiplanos altos, de relieve bajo y
# pendiente suave, predominantemente sobre rocas plutonicas").
#
# Metodo del libro utilizado: tabla de medias por grupo (groupby + mean) y
# heatmap normalizado, igual que se sugiere en la Actividad 3 de
# "08_ClusterEspacial".
# ----------------------------------------------------------------------------
perfil_clusters = gdf.groupby("cluster_kmeans")[variables_cluster].mean()
print("\nPerfil promedio por cluster (K-means):")
print(perfil_clusters)

# Heatmap normalizado (z-score por columna) para comparar visualmente el
# perfil de cada cluster en una misma escala.
perfil_normalizado = (perfil_clusters - perfil_clusters.mean()) / perfil_clusters.std()

plt.figure(figsize=(8, 4))
sns.heatmap(perfil_normalizado.T, annot=perfil_clusters.T, fmt=".1f", cmap="RdBu_r", center=0)
plt.title("Perfil de cada cluster (color = z-score, numero = valor real)")
plt.xlabel("Cluster")
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "05_heatmap_perfil_clusters.png"), dpi=150)
plt.show()

# Composicion litologica dominante por cluster (variable categorica que se
# dejo fuera del algoritmo, pero es muy util para interpretar los grupos).
composicion_geologia = pd.crosstab(gdf["cluster_kmeans"], gdf["Geología"], normalize="index") * 100
print("\nComposicion litologica por cluster (% de poligonos):")
print(composicion_geologia.round(1))


# %% [11] EXPORTAR RESULTADOS
# ----------------------------------------------------------------------------
# Que se busca: guardar el GeoDataFrame con las columnas de cluster
# añadidas, para poder abrirlo en ArcGIS/QGIS o reutilizarlo en el
# siguiente paso del trabajo (autocorrelacion espacial / regresion).
# ----------------------------------------------------------------------------
ruta_salida = os.path.join(CARPETA_RESULTADOS, "altiplanos_clasificados.gpkg")
gdf.to_file(ruta_salida, driver="GPKG")
print(f"\nResultado guardado en: {ruta_salida}")

# %% [12] MODELO ALTERNATIVO: TimeSeriesKMeans CON DISTANCIA DTW
# ----------------------------------------------------------------------------
# Que se busca:
#   K-means y Ward (secciones 7-8) miden la similitud entre dos altiplanos
#   con distancia EUCLIDIANA: cada variable estandarizada pesa por separado y
#   de forma independiente. Aqui se prueba una alternativa: tratar el perfil
#   morfometrico de cada altiplano (sus 9 variables estandarizadas, en el
#   mismo orden para todos los poligonos) como una "secuencia", y agruparlos
#   con Dynamic Time Warping (DTW), una distancia que permite "estirar" o
#   "comprimir" localmente la secuencia al compararla con otra, capturando
#   similitud de FORMA del perfil en vez de solo la diferencia punto a punto.
#   Esto es exploratorio: no viene del libro del curso, sino que se
#   encontro en las pruebas previas de este mismo proyecto (notebook de
#   clustering en Google Colab), donde ya se habia probado esta tecnica.
#
# Metodo usado: `tslearn.clustering.TimeSeriesKMeans` con `metric="dtw"`.
#
# Ventajas / desventajas de DTW frente a K-means/Ward euclidiano:
#   (+) Puede agrupar altiplanos con un perfil de variables "similar en
#       forma" aunque haya pequeños desfaces entre variables individuales,
#       algo que la distancia euclidiana penaliza de forma mas rigida.
#   (-) Interpretacion conceptualmente forzada: a diferencia de una serie de
#       tiempo real, aqui NO existe una nocion natural de "antes/despues"
#       entre Altitud_X, Altitud_St, Alt_90, etc. -- el orden de las
#       variables es arbitrario, así que el "warping" que hace DTW no tiene
#       un significado fisico tan claro como en datos temporales genuinos.
#   (-) Mucho mas lento que K-means: en pruebas con este dataset (491
#       poligonos, 9 variables), un solo ajuste tardo entre ~10 y ~60
#       segundos dependiendo de k, frente a milisegundos de K-means. Por
#       eso aqui se prueba solo una lista acotada de valores de k (no un
#       barrido 2-50 completo como en la seccion 6).
#   (-) No admite una restriccion de conectividad espacial (a diferencia de
#       AgglomerativeClustering en "02_clustering_espacial_altiplanos.py"),
#       asi que esta comparacion queda limitada al caso NO espacial.
# ----------------------------------------------------------------------------
k_dtw_candidatos = [2, 3, 4, 5, 6, 8, 10, 15, 20]
resultados_dtw = []

print("\nAjustando TimeSeriesKMeans (DTW) para varios valores de k (puede tardar varios minutos)...")
for k in k_dtw_candidatos:
    modelo_dtw = TimeSeriesKMeans(n_clusters=k, metric="dtw", random_state=SEMILLA, n_jobs=-1)
    etiquetas_dtw = modelo_dtw.fit_predict(X_estandarizado)
    silueta_dtw = silhouette_score(X_estandarizado, etiquetas_dtw)
    ch_dtw = calinski_harabasz_score(X_estandarizado, etiquetas_dtw)
    resultados_dtw.append({"k": k, "silhouette": silueta_dtw, "calinski_harabasz": ch_dtw})
    print(f"  k={k}: silhouette={silueta_dtw:.3f}  calinski_harabasz={ch_dtw:.1f}")

resultados_dtw = pd.DataFrame(resultados_dtw)

# Comparacion directa: para los mismos valores de k, ?que tanto mejor o peor
# es DTW frente a K-means euclidiano (seccion 6)?
siluetas_kmeans_dict = dict(zip(rango_k, siluetas))
resultados_dtw["silhouette_kmeans"] = resultados_dtw["k"].map(siluetas_kmeans_dict)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(resultados_dtw["k"], resultados_dtw["silhouette"], marker="o", label="TimeSeriesKMeans (DTW)", color="mediumpurple")
ax.plot(resultados_dtw["k"], resultados_dtw["silhouette_kmeans"], marker="o", label="K-means (euclidiano)", color="darkorange")
ax.set_xlabel("Numero de clusters (k)")
ax.set_ylabel("Coeficiente de Silhouette")
ax.set_title("DTW vs. K-means euclidiano")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(CARPETA_RESULTADOS, "06_dtw_vs_kmeans.png"), dpi=150)
plt.show()

print("\nComparacion DTW vs. K-means (mismo k):")
print(resultados_dtw)

# ============================================================================
# SIGUIENTES PASOS SUGERIDOS (fuera del alcance de este script):
#   - Con la columna "cluster_kmeans" ya asignada, se podria explorar si
#     existe autocorrelacion espacial en la UBICACION de cada tipo (p.ej.
#     usando una matriz de pesos por distancia entre centroides, ya que la
#     contiguidad tipo Queen no aplica aqui), siguiendo el notebook
#     "07_MatrizCorrelacion".
#   - Definir una variable respuesta (Y) para pasar a un modelo de
#     regresion (GLM del notebook "04_GLMPhyton") si el trabajo final
#     busca EXPLICAR por que ciertos altiplanos son de un tipo u otro en
#     funcion de covariables adicionales (geologia, precipitacion, etc.).
# ============================================================================
