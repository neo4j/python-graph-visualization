import numpy as np
from matplotlib.colors import LinearSegmentedColormap as lsc
from neo4j_viz.colors import _NEO4J_COLORS_CONTINUOUS_BASE

color_map = lsc.from_list("neo4j", _NEO4J_COLORS_CONTINUOUS_BASE, N=256)

colors_array = np.linspace(0, 1, 256)
# print(colors_array)

color_tuples = [
    (round(a[0] * 255), round(a[1] * 255), round(a[2] * 255))
    for a in color_map(colors_array)
]
print(color_tuples)
