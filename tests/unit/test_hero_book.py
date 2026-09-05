from __future__ import annotations

import math
import re
from xml.etree import ElementTree

from src.hero_book import hero_book_scene_svg


def _scene() -> ElementTree.Element:
    return ElementTree.fromstring(hero_book_scene_svg())


def _with_class(root: ElementTree.Element, class_name: str) -> list[ElementTree.Element]:
    return [node for node in root.iter() if class_name in node.get("class", "").split()]


def test_hero_book_is_accessible_decorative_responsive_svg():
    root = _scene()
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("viewBox") == "0 0 720 500"
    assert root.get("aria-hidden") == "true"
    assert root.get("focusable") == "false"
    assert root.get("width") is None
    assert root.get("height") is None
    assert _with_class(root, "atlas-book-scene") == [root]


def test_hero_book_gradients_and_local_references_resolve_uniquely():
    root = _scene()
    ids = [node.get("id") for node in root.iter() if node.get("id")]
    assert len(ids) == len(set(ids))
    gradients = [node for node in root.iter() if node.tag.endswith("Gradient")]
    assert len(gradients) >= 10
    assert {node.get("id") for node in gradients} >= {
        "atlasBookCover", "atlasBookLeftPaper", "atlasBookRightPaper",
        "atlasBookRaisedPaper", "atlasBookFold", "atlasBookPaperBlock",
    }
    referenced_ids = re.findall(r"url\(#([^)]+)\)", hero_book_scene_svg())
    assert referenced_ids
    assert set(referenced_ids).issubset(set(ids))


def test_hero_book_keeps_separate_model_surfaces_and_motion_layers():
    root = _scene()
    for class_name in (
        "atlas-book-cover", "atlas-book-pages", "atlas-book-leaf",
        "atlas-book-spine", "atlas-book-page-left", "atlas-book-page-right",
        "atlas-book-page-edges", "atlas-book-network", "atlas-book-flow",
        "atlas-book-aura", "atlas-book-ground", "atlas-book-page-diagram",
    ):
        assert _with_class(root, class_name), class_name
    edges = _with_class(root, "atlas-book-page-edges")[0]
    assert len(edges) == 15
    left = _with_class(root, "atlas-book-page-left")[0]
    right = _with_class(root, "atlas-book-page-right")[0]
    assert left.get("fill") != right.get("fill")
    assert left.get("d") != right.get("d")
    assert 5 <= len(_with_class(root, "atlas-book-node")) <= 10
    assert _with_class(_with_class(root, "atlas-book-pages")[0], "atlas-book-leaf")


def test_hero_observatory_has_layered_glass_intelligence_and_book_projection():
    root = _scene()
    for class_name in (
        "atlas-observatory-guides", "atlas-book-core", "atlas-book-core-lattice",
        "atlas-book-orbit-back", "atlas-book-orbit", "atlas-book-projection",
        "atlas-book-memory", "atlas-book-signal",
    ):
        assert _with_class(root, class_name), class_name
    core = _with_class(root, "atlas-book-core")[0]
    assert len(_with_class(core, "atlas-book-node")) == 8
    assert _with_class(core, "atlas-book-core-lattice")
    projection = _with_class(root, "atlas-book-projection")[0]
    assert len(_with_class(projection, "atlas-book-flow")) == 2
    gradient_ids = {node.get("id") for node in root.iter() if node.tag.endswith("Gradient")}
    assert {"atlasLensGlass", "atlasLensLight", "atlasLensRim", "atlasOrbitLight", "atlasProjection"} <= gradient_ids
    # Compose the smaller physical book with a parent transform, leaving the
    # child free for CSS float motion without overriding its perspective.
    book_layer = _with_class(root, "atlas-book-pages")[0]
    parent = next(node for node in root.iter() if book_layer in list(node))
    assert parent.get("transform") == "translate(55 80) scale(.84)"


def test_hero_book_is_self_contained_and_can_be_paused_entirely_by_css():
    svg = hero_book_scene_svg()
    root = _scene()
    forbidden_tags = {"script", "image", "foreignObject", "animate", "animateMotion", "animateTransform", "set"}
    for node in root.iter():
        local_name = node.tag.rsplit("}", 1)[-1]
        assert local_name not in forbidden_tags
        for key, value in node.attrib.items():
            assert not key.lower().startswith("on")
            assert key.rsplit("}", 1)[-1] not in {"href", "src"}
            assert "http://" not in value and "https://" not in value
            assert "javascript:" not in value.lower()
    # The namespace declaration identifies SVG; it is not a fetched asset.
    assert svg.count("http://") == 1
    assert "__PAPER_EDGES__" not in svg
    assert "__LEFT_INK__" not in svg
    assert "__NODES__" not in svg
    assert re.search(r"\b(?:nan|infinity|inf)\b", svg, re.IGNORECASE) is None
    for number in re.findall(r"(?<![\w#])[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", svg):
        assert math.isfinite(float(number))
    assert len(svg) < 24_000
    assert svg == hero_book_scene_svg()
