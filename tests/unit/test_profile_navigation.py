from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest

from src.profile_navigation import learning_profile_url, new_learning_profile_url
from src.ui import mobile_navigation_html, profile_return_html, sidebar_navigation_html


class _NavigationParser(HTMLParser):
    """Inspect links and their visible labels without optional DOM dependencies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ancestors: list[tuple[str, dict[str, str | None]]] = []
        self.links: list[dict] = []
        self.current_link: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            self.current_link = {
                "attributes": attributes,
                "ancestors": list(self.ancestors),
                "text": [],
            }
            self.links.append(self.current_link)
        if tag not in {"area", "br", "hr", "img", "input", "link", "meta", "wbr"}:
            self.ancestors.append((tag, attributes))

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.current_link = None
        for index in range(len(self.ancestors) - 1, -1, -1):
            if self.ancestors[index][0] == tag:
                del self.ancestors[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.current_link is not None:
            self.current_link["text"].append(data)


def _new_profile_params(url: str, is_zh: bool, previous_id: str) -> dict[str, list[str]]:
    parsed = urlsplit(url)
    assert parsed.scheme == ""
    assert parsed.netloc == ""
    assert parsed.path == ""
    assert parsed.fragment == "learning-brief"
    params = parse_qs(parsed.query)
    assert set(params) == {"ui_language", "user_id", "new_profile", "return_profile", "return_language"}
    assert params["ui_language"] == ["zh" if is_zh else "en"]
    assert params["new_profile"] == ["1"]
    assert params["return_profile"] == [previous_id]
    assert params["return_language"] == ["zh" if is_zh else "en"]
    profile_id = params["user_id"][0]
    assert profile_id.startswith("learner-")
    assert profile_id != previous_id
    assert re.fullmatch(r"learner-[0-9a-f]{12,32}", profile_id)
    return params


@pytest.mark.parametrize("is_zh", [True, False])
def test_new_profile_url_starts_a_fresh_workspace_in_current_language(is_zh: bool) -> None:
    _new_profile_params(new_learning_profile_url(is_zh, "demo-eee"), is_zh, "demo-eee")


def test_every_new_profile_entry_gets_a_unique_identifier() -> None:
    identifiers = {
        _new_profile_params(new_learning_profile_url(True, "demo-eee"), True, "demo-eee")["user_id"][0]
        for _ in range(20)
    }
    assert len(identifiers) == 20


@pytest.mark.parametrize("is_zh", [True, False])
@pytest.mark.parametrize(
    "previous_id",
    [
        "我的学习档案 / 科研",
        "reader+one&book_query=old-book#reading-route",
        'reader\"<script>alert(1)</script>?history=1&preview_plan=2',
        "student@example.com",
    ],
)
def test_previous_profile_id_round_trips_without_injecting_navigation_state(
    is_zh: bool, previous_id: str
) -> None:
    _new_profile_params(new_learning_profile_url(is_zh, previous_id), is_zh, previous_id)


@pytest.mark.parametrize("render_navigation", [sidebar_navigation_html, mobile_navigation_html])
@pytest.mark.parametrize("is_zh", [True, False])
@pytest.mark.parametrize("preview", [True, False])
def test_new_profile_is_visible_on_desktop_mobile_and_history_views(
    render_navigation, is_zh: bool, preview: bool
) -> None:
    previous_id = "我的档案 & demo-eee"
    markup = render_navigation(is_zh, previous_id, preview=preview)
    parser = _NavigationParser()
    parser.feed(markup)
    label = "新建学习档案" if is_zh else "New learning profile"
    matching = [link for link in parser.links if label in " ".join(link["text"]).strip()]
    assert len(matching) == 1
    link = matching[0]
    assert link["attributes"].get("target") == "_self"
    assert link["attributes"].get("aria-hidden") != "true"
    assert "hidden" not in link["attributes"]
    _new_profile_params(link["attributes"]["href"], is_zh, previous_id)

    # Creating a workspace must not be mistaken for a scroll-only section link.
    assert not any(
        "atlas-side-nav" in (attrs.get("class") or "").split()
        for _, attrs in link["ancestors"]
    )
    parent_attrs = link["ancestors"][-1][1] if link["ancestors"] else {}
    direct_parent_classes = (parent_attrs.get("class") or "").split()
    assert "atlas-mobile-nav-panel" not in direct_parent_classes


@pytest.mark.parametrize("is_zh", [True, False])
def test_return_link_reopens_only_the_previous_profile(is_zh: bool) -> None:
    previous_id = '旧档案 \"<script>alert(1)</script>&history=1'
    url = urlsplit(learning_profile_url(is_zh, previous_id))
    assert url.scheme == url.netloc == url.path == ""
    assert url.fragment == "reading-journey"
    assert parse_qs(url.query) == {
        "ui_language": ["zh" if is_zh else "en"],
        "user_id": [previous_id],
    }
    markup = profile_return_html(is_zh, previous_id)
    assert "<script>" not in markup
    parser = _NavigationParser()
    parser.feed(markup)
    assert len(parser.links) == 1
    link = parser.links[0]
    assert link["attributes"]["href"] == learning_profile_url(is_zh, previous_id)
    assert link["attributes"]["target"] == "_self"
    label = "返回原学习档案" if is_zh else "Back to previous profile"
    assert label in " ".join(link["text"])
    assert previous_id in " ".join(link["text"])


@pytest.mark.parametrize("is_zh", [True, False])
def test_mobile_language_switch_keeps_new_profile_and_return_destination(is_zh: bool) -> None:
    draft_id = "learner-0123456789ab"
    previous_id = "原档案 & book_query=not-a-query"
    previous_language = "en" if is_zh else "zh"
    parser = _NavigationParser()
    parser.feed(mobile_navigation_html(
        is_zh, draft_id, return_profile_id=previous_id, return_language=previous_language
    ))
    for language, label in [("en", "English"), ("zh", "中文")]:
        link = next(link for link in parser.links if "".join(link["text"]).strip() == label)
        url = urlsplit(link["attributes"]["href"])
        assert url.scheme == url.netloc == url.path == ""
        assert url.fragment == "learning-brief"
        assert parse_qs(url.query) == {
            "ui_language": [language],
            "set_language": [language],
            "user_id": [draft_id],
            "new_profile": ["1"],
            "return_profile": [previous_id],
            "return_language": [previous_language],
        }


@pytest.mark.parametrize("is_zh", [True, False])
def test_return_after_language_switch_opens_original_language_workspace(is_zh: bool) -> None:
    previous_language = "en" if is_zh else "zh"
    previous_id = "original-profile"
    parser = _NavigationParser()
    parser.feed(profile_return_html(is_zh, previous_id, return_language=previous_language))
    link = parser.links[0]
    assert parse_qs(urlsplit(link["attributes"]["href"]).query) == {
        "ui_language": [previous_language],
        "user_id": [previous_id],
    }
    label = "返回原学习档案" if is_zh else "Back to previous profile"
    assert label in " ".join(link["text"])
