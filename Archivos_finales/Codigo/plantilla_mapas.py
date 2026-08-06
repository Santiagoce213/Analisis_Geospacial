"""
Plantilla cartografica reutilizable para todos los mapas del proyecto.

Capas de contexto: hillshade (40% de transparencia) + borde del area de estudio.
Elementos cartograficos: flecha de norte (superior izquierda), leyenda (junto al norte,
hacia el centro) y escala grafica de franjas negras/blancas en km (inferior derecha, con
una etiqueta numerica en cada frontera de franja).

Uso tipico dentro de un notebook (en una celda NUEVA, separada de la celda que hace el
analisis y genera la figura original):

    import sys
    sys.path.insert(0, os.getcwd())
    from plantilla_mapas import aplicar_plantilla_mapa, posicionar_leyenda

    fig, ax = plt.subplots(1, figsize=(10, 10))
    ancla = aplicar_plantilla_mapa(ax)                    # dibuja hillshade+area+norte+escala
    gdf.plot(column="...", ax=ax, alpha=0.8, zorder=5,    # alpha=0.8 = 20% transparencia
             legend=True, legend_kwds=posicionar_leyenda(ax, ancla, titulo="..."))
    ax.set_title("...")
    ax.set_axis_off()
    plt.savefig(os.path.join(CARPETA_IMAGENES, "nombre_figura.png"), dpi=150)

Aprobado por el usuario el 2026-07-17 tras iterar sobre `01_clustering_altiplanos_v2.ipynb`
(mapa de clusters K-means) -- ver `CONTEXTO_PROYECTO_v2.md` para el detalle de las
decisiones de diseno (por que se ancla en coordenadas de datos y no en fraccion de ejes,
por que se usa realce de contraste en el hillshade, etc.).
"""
import os

import numpy as np
import rasterio
import geopandas as gpd
from matplotlib.patches import Rectangle

RUTA_HILLSHADE = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Raster\50m_UTM\Hillshade_50.tif"
RUTA_AREA_ESTUDIO = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Capas\Area_Estudio.shp"
CARPETA_IMAGENES = r"C:\Users\MSI\Desktop\Universidad\Analisis_Geoespacial\Imágenes"


def agregar_hillshade(ax, ruta_hillshade=RUTA_HILLSHADE, alpha=0.6, estirar_contraste=True):
    """Dibuja el hillshade en escala de grises. alpha=0.6 equivale a 40% de transparencia
    (instruccion del usuario: "40% de transparencia" = 60% de opacidad).

    estirar_contraste: aplica un realce de contraste (percentiles 2-98) antes de dibujar --
    el hillshade original es bastante claro/plano en promedio (media=168 de 255) y se ve
    muy lavado una vez mezclado con transparencia sobre fondo blanco sin este ajuste.
    """
    with rasterio.open(ruta_hillshade) as src:
        banda = src.read(1).astype(np.float32)
        if src.nodata is not None:
            banda = np.where(banda == src.nodata, np.nan, banda)
        izquierda, abajo, derecha, arriba = src.bounds

    vmin, vmax = np.nanpercentile(banda, [2, 98]) if estirar_contraste else (0, 255)
    ax.imshow(banda, cmap="gray", extent=(izquierda, derecha, abajo, arriba),
              alpha=alpha, zorder=0, interpolation="bilinear", vmin=vmin, vmax=vmax)


def agregar_area_estudio(ax, ruta_area_estudio=RUTA_AREA_ESTUDIO, crs_destino=None,
                          edgecolor="black", linewidth=1.2):
    """Dibuja SOLO el borde del area de estudio (sin relleno, para no tapar el hillshade ni los datos)."""
    area = gpd.read_file(ruta_area_estudio)
    if crs_destino is not None and area.crs != crs_destino:
        area = area.to_crs(crs_destino)
    area.boundary.plot(ax=ax, edgecolor=edgecolor, linewidth=linewidth, zorder=1)
    return area


def agregar_flecha_norte(ax, ubicacion="superior izquierda", margen_relativo=0.06, alto_relativo=0.07):
    """Flecha de norte, anclada en COORDENADAS DE DATOS (no en fraccion de ejes): con aspecto
    'equal' y un area de estudio no cuadrada, la fraccion de ejes puede quedar desalineada
    del mapa realmente dibujado. Anclar en coordenadas de datos la deja pegada al mapa.

    Devuelve (x, y_tope) -- la esquina superior de la flecha, util para ubicar la leyenda
    justo al lado (ver `posicionar_leyenda`).
    """
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    ancho_m, alto_m = xlim[1] - xlim[0], ylim[1] - ylim[0]

    x = xlim[0] + ancho_m * margen_relativo if "izquierda" in ubicacion else xlim[1] - ancho_m * margen_relativo
    if "superior" in ubicacion:
        y_top = ylim[1] - alto_m * margen_relativo
        y_base = y_top - alto_m * alto_relativo
    else:
        y_base = ylim[0] + alto_m * margen_relativo
        y_top = y_base + alto_m * alto_relativo

    ax.annotate("", xy=(x, y_top), xytext=(x, y_base), xycoords="data", textcoords="data",
                arrowprops=dict(facecolor="black", edgecolor="black", width=4, headwidth=13, headlength=11),
                zorder=10)
    ax.text(x, y_top + alto_m * 0.015, "N", ha="center", va="bottom",
            fontsize=13, fontweight="bold", zorder=10)
    return x, y_top


def agregar_escala_grafica(ax, longitud_km=None, num_segmentos=4, margen_relativo=0.05, ubicacion="inferior derecha"):
    """Escala grafica de franjas negras/blancas alternadas, en km, anclada en coordenadas de
    datos. Muestra una etiqueta numerica en cada frontera de franja (incluye "0" al inicio
    y una etiqueta al final de cada una de las `num_segmentos` franjas).
    """
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    ancho_m, alto_m = xlim[1] - xlim[0], ylim[1] - ylim[0]

    if longitud_km is None:
        objetivo_m = ancho_m * 0.28
        candidatos_km = [1, 2, 4, 5, 8, 10, 15, 20, 25, 40, 50, 75, 100, 150, 200, 250]
        longitud_km = min(candidatos_km, key=lambda k: abs(k * 1000 - objetivo_m))

    longitud_m = longitud_km * 1000
    segmento_m = longitud_m / num_segmentos
    segmento_km = longitud_km / num_segmentos
    alto_barra = alto_m * 0.010

    x0 = (xlim[1] - ancho_m * margen_relativo - longitud_m if ubicacion == "inferior derecha"
          else xlim[0] + ancho_m * margen_relativo)
    y0 = ylim[0] + alto_m * margen_relativo

    for i in range(num_segmentos):
        color = "black" if i % 2 == 0 else "white"
        ax.add_patch(Rectangle((x0 + i * segmento_m, y0), segmento_m, alto_barra,
                                facecolor=color, edgecolor="black", linewidth=0.6, zorder=10))

    ax.text(x0, y0 + alto_barra * 1.6, "0", ha="center", va="bottom", fontsize=7.5, zorder=10)
    for i in range(1, num_segmentos + 1):
        valor_km = segmento_km * i
        etiqueta = f"{valor_km:.0f} km" if i == num_segmentos else f"{valor_km:.0f}"
        ax.text(x0 + segmento_m * i, y0 + alto_barra * 1.6, etiqueta,
                ha="center", va="bottom", fontsize=7.5, zorder=10)


def aplicar_plantilla_mapa(ax, extent_de=None, alpha_hillshade=0.6,
                            ubicacion_norte="superior izquierda", ubicacion_escala="inferior derecha"):
    """Aplica hillshade + area de estudio + norte + escala a un eje.

    Llamar ANTES de graficar los datos del analisis sobre `ax`, para que el hillshade y el
    borde del area de estudio queden debajo (zorder bajo) y los datos encima.

    extent_de: GeoDataFrame opcional para fijar el extent del mapa al de sus propios datos
    (con 5% de margen); si es None, se usa el extent del area de estudio completa.

    Devuelve un dict con el ancla de la flecha de norte, para pasarselo a `posicionar_leyenda`.
    """
    agregar_hillshade(ax, alpha=alpha_hillshade)
    area = agregar_area_estudio(ax)

    xmin, ymin, xmax, ymax = extent_de.total_bounds if extent_de is not None else area.total_bounds
    margen_x, margen_y = (xmax - xmin) * 0.05, (ymax - ymin) * 0.05
    ax.set_xlim(xmin - margen_x, xmax + margen_x)
    ax.set_ylim(ymin - margen_y, ymax + margen_y)

    x_norte, y_norte_tope = agregar_flecha_norte(ax, ubicacion=ubicacion_norte)
    agregar_escala_grafica(ax, ubicacion=ubicacion_escala)
    return {"x_norte": x_norte, "y_norte_tope": y_norte_tope}


def posicionar_leyenda(ax, ancla, titulo=None, desplazamiento_x_relativo=0.05):
    """Arma el dict `legend_kwds` para que la leyenda quede justo al lado de la flecha de
    norte (un poco hacia el centro del mapa), anclada en las mismas coordenadas de datos.

    Uso: gdf.plot(..., legend=True, legend_kwds=posicionar_leyenda(ax, ancla, titulo="Cluster"))
    """
    ancho_m = ax.get_xlim()[1] - ax.get_xlim()[0]
    kwds = {
        "bbox_to_anchor": (ancla["x_norte"] + ancho_m * desplazamiento_x_relativo, ancla["y_norte_tope"]),
        "bbox_transform": ax.transData,
        "loc": "upper left",
    }
    if titulo is not None:
        kwds["title"] = titulo
    return kwds
