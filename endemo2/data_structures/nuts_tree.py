"""
This module contains everything one needs to represent NUTS regions as a tree structure.
The leafs are NUTS2 regions, the root is the 2-letter country code and the in-between-nodes are for navigation.
"""
from __future__ import annotations

from typing import Any, Union


class NutsRegion:
    """
    Represents one NUTS Region according to individual codes.

    :param str region_name: The NUTS tag of the region. For example: DE, DE1, DE11, ...

    :ivar str region_name: The NUTS tag of the region. For example: DE, DE1, DE11, ...
    """
    def __init__(self, region_name: str):
        self.region_name = region_name


class NutsRegionLeaf(NutsRegion):
    """
    Represents one NUTS2 Region according to individual codes. It is the leaf of the NUTS tree.

    :param str region_name: The NUTS tag of the region. For example: DE11, DE12 ...
    :param Any data: The timeseries for the value the tree is associated with. This can be any type of data.

    :ivar str region_name: The NUTS tag of the region. For example: DE11, DE12 ...
    :ivar Any data: The timeseries for the value the tree is associated with. This can be any type of data.
    """
    def __init__(self, region_name: str, data: Any):
        super().__init__(region_name)
        self.data = data

    def __str__(self):
        return "[leaf: " + self.region_name + "]"

    def get(self):
        """ Getter for the leaf's data. """
        return self.data


class NutsRegionNode(NutsRegion):
    """
    Represents one NUTS Region according to individual codes. Not a NUTS2 region, but a node in the tree.

    :param str region_name: The NUTS tag of the region. For example: DE, DE1, DE2, ...

    :ivar str region_name: The NUTS tag of the region. For example: DE, DE1, DE2, ...
    :ivar dict[str, NutsRegion] _subregions: The child regions, accessible per NUTS tag. For DE: {DE1 -> .., DE2 -> ..}
    """

    def __init__(self, region_name: str):
        super().__init__(region_name)
        self._sub_regions = dict[str, Union[NutsRegionNode, NutsRegionLeaf]]()

    def __str__(self):
        out = "[root: " + self.region_name + ", children: "
        for key, value in self._sub_regions.items():
            out += key + ", "
        out += "]"
        for _, child in self._sub_regions.items():
            out += str(child)
        return out

    def get_region_name(self):
        """ Getter for the region_name. """
        return self.region_name

    def add_leaf_region(self, nuts2region_obj: NutsRegionLeaf) -> None:
        """
        Traverses the NUTS Tree recursively to insert a leaf node.

        :param nuts2region_obj: The NutsRegionLeaf object to insert into the tree
        """
        if len(self.region_name) + 1 is len(nuts2region_obj.region_name):
            # region is direct subregion
            self._sub_regions[nuts2region_obj.region_name] = nuts2region_obj
        elif len(self.region_name) + 1 < len(nuts2region_obj.region_name):
            # region is a subregion of a subregion, search for right one to insert
            for key, value in self._sub_regions.items():
                if nuts2region_obj.region_name.startswith(key):
                    # found parent region
                    self._sub_regions[key].add_leaf_region(nuts2region_obj)
                    return
            # found no region, create in-between
            new_inbetween_region_name = nuts2region_obj.region_name[:len(self.region_name)+1]
            new_inbetween_obj = NutsRegionNode(new_inbetween_region_name)
            new_inbetween_obj.add_leaf_region(nuts2region_obj)
            self._sub_regions[new_inbetween_region_name] = new_inbetween_obj

    def get_specific_node(self, region_code: str) -> NutsRegion:
        """
        Traverse tree and find the node with region code.

        :param region_code: The region code of the node to find.
        :return: The NutsRegion object of the region with region_code.
        """
        if len(self.region_name) + 1 is len(region_code):
            # region is direct subregion
            return self._sub_regions[region_code]
        elif len(self.region_name) + 1 < len(region_code):
            # region is a subregion of a subregion, search for right one to insert
            for key, value in self._sub_regions.items():
                if region_code.startswith(key):
                    # found parent region
                    return self._sub_regions[key].get_specific_node(region_code)

    def get_nodes_dfs(self) -> list[NutsRegion]:
        """
        Get a list of all nodes in Depth-First-Search order.
        Used mostly for debugging purposes.

        :return: The list of nodes in DFS-order.
        """
        if len(self._sub_regions) == 0:
            # leaf node, return only self
            return [self]
        else:
            # recursively return this node and all children
            nodes = [self]
            for subregion in self._sub_regions.values():
                nodes += subregion.get_nodes_dfs()
            return nodes

    def get_all_leaf_nodes(self) -> list[NutsRegionLeaf]:
        """
        Get a list of all leaf nodes.

        :return: The list of leaf nodes.
        """
        if len(self._sub_regions) == 0:
            # leaf node, return only self
            return [self]
        else:
            # recursively return this node and all children
            nodes = []
            for subregion in self._sub_regions.values():
                if isinstance(subregion, NutsRegionLeaf):
                    nodes.append(subregion)
                else:
                    nodes += subregion.get_all_leaf_nodes()
            return nodes


