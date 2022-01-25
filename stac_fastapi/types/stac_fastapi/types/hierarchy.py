"""Types and functions for browsable and children conformance class support.

The types contained in this file provide the tooling necessary to support hierarchy within a
STAC API. The various nodes are recursively parsed from a dict which can (e.g.) be generated by
json.load. A minimal, STAC compliant catalog can be generated from a catalog node (refer to a
node's id field name: it will either be catalog_id or collection_id) with the browsable_catalog
function.
"""
from typing import List, Optional, Tuple, TypedDict, Union
from urllib.parse import urljoin

from stac_pydantic import Catalog
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes
from stac_pydantic.version import STAC_VERSION

ItemPath = Tuple[str, str]
NodeType = str


class BrowsableNode(TypedDict):
    """Abstract node for defining browsable hierarchy."""

    children: List[Union["CatalogNode", "CollectionNode"]]
    items: List[ItemPath]


class CollectionNode(BrowsableNode):
    """Node for collections in browsable hierarchy."""

    collection_id: str


class CatalogNode(BrowsableNode):
    """Node for collections in browsable hierarchy."""

    catalog_id: str
    title: Optional[str]
    description: Optional[str]


def browsable_child_link(node: BrowsableNode, base_url: str) -> str:
    """Produce browsable link to a child."""
    if "collection_id" in node:
        return {
            "rel": Relations.child.value,
            "type": MimeTypes.json,
            "title": node.get("title") or node.get("collection_id"),
            "href": urljoin([base_url, f"collections/{node['collection_id']}"]),
        }
    elif "catalog_id" in node:
        return {
            "rel": Relations.child.value,
            "type": MimeTypes.json,
            "title": node.get("title") or node.get("catalog_id"),
            "href": "/".join([base_url.strip("/"), node["catalog_id"]]),
        }


def browsable_item_link(item_path: ItemPath, base_url):
    """Produce browsable link to an item."""
    return {
        "rel": Relations.item.value,
        "type": MimeTypes.json,
        "href": urljoin(base_url, f"collections/{item_path[0]}/items/{item_path[1]}"),
    }


def browsable_catalog(node: CatalogNode, catalog_path: str, base_url: str) -> Catalog:
    """Generate a catalog based on a CatalogNode in a BrowsableNode tree."""
    children_links = [
        browsable_child_link(child, base_url) for child in node["children"]
    ]
    item_links = [browsable_item_link(item, base_url) for item in node["items"]]
    standard_links = [
        {
            "rel": Relations.root.value,
            "type": MimeTypes.json,
            "href": base_url,
        },
        {
            "rel": Relations.self.value,
            "type": MimeTypes.json,
            "href": urljoin(base_url, f"/catalogs/{catalog_path.strip('/')}"),
        },
    ]
    return Catalog(
        type="Catalog",
        id=node["catalog_id"],
        description=node.get("description")
        or f"Generated description for {node['catalog_id']}",
        stac_version=STAC_VERSION,
        links=children_links + item_links + standard_links,
    )


def parse_hierarchy(d: dict) -> BrowsableNode:
    """Parse a dictionary as a BrowsableNode tree."""
    if "children" in d:
        children = [parse_hierarchy(child) for child in d["children"]]
    else:
        children = []

    if "collection_id" in d:
        return CollectionNode(
            collection_id=d["collection_id"], children=children, items=d.get("items")
        )
    elif "catalog_id" in d:
        return CatalogNode(
            catalog_id=d["catalog_id"],
            children=children,
            items=d.get("items"),
            title=d.get("title"),
            description=d.get("description"),
        )
    else:
        return BrowsableNode(children=children, items=d.get("items"))