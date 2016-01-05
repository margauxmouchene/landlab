import numpy as np
from scipy.spatial import Voronoi
from scipy.spatial import Delaunay

from .graph import Graph


class VoronoiGraph(Graph):

    """Graph of a voronoi grid.

    Examples
    --------
    >>> from landlab.graph import VoronoiGraph
    """

    def __init__(self, nodes):
        """Create a voronoi grid.

        Parameters
        ----------
        nodes : tuple of array_like
            Coordinates of every node. First *y*, then *x*.

        Examples
        --------
        >>> from landlab.graph import VoronoiGraph
        >>> node_x = [0, 1, 2,
        ...           1, 2, 3]
        >>> node_y = [0, 0, 0,
        ...           2, 2, 2]
        >>> graph = VoronoiGraph((node_y, node_x))
        >>> graph.x_of_node
        array([ 0.,  1.,  2.,  1.,  2.,  3.])
        >>> graph.y_of_node
        array([ 0.,  0.,  0.,  2.,  2.,  2.])
        >>> graph.nodes_at_link # doctest: +NORMALIZE_WHITESPACE
        array([[3, 0], [0, 1], [1, 3], [2, 5], [5, 4], [4, 2], [1, 2], [4, 1],
               [4, 3]])
        >>> graph.links_at_node # doctest: +NORMALIZE_WHITESPACE
        array([[ 0,  1, -1, -1], [ 1,  2,  6,  7], [ 3,  5,  6, -1],
               [ 0,  2,  8, -1], [ 4,  5,  7,  8], [ 3,  4, -1, -1]])
        >>> graph.nodes_at_patch # doctest: +NORMALIZE_WHITESPACE
        array([[0, 1, 3], [2, 4, 5], [1, 2, 4], [1, 3, 4]])

        >>> import numpy as np
        >>> node_x = np.random.random(10000)
        >>> node_y = np.random.random(10000)
        >>> graph = VoronoiGraph((node_y, node_x))
        """
        from .cfuncs import _setup_links_at_patch

        node_y, node_x = (np.asarray(nodes[0], dtype=float),
                          np.asarray(nodes[1], dtype=float))

        points = np.array(zip(node_x, node_y), dtype=float)
        delaunay = Delaunay(points)
        nodes_at_patch = delaunay.simplices

        n_patches = len(nodes_at_patch)
        n_shared_links = np.count_nonzero(delaunay.neighbors > -1)
        n_links = 3 * n_patches - n_shared_links // 2

        links_at_patch = np.empty((n_patches, 3), dtype=int)
        nodes_at_link = np.empty((n_links, 2), dtype=int)

        _setup_links_at_patch(np.array(delaunay.simplices, dtype=int),
                              np.array(delaunay.neighbors, dtype=int),
                              nodes_at_link, links_at_patch)

        super(VoronoiGraph, self).__init__((node_y.flat, node_x.flat),
                                           links=nodes_at_link,
                                           patches=links_at_patch)