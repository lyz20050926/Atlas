from urllib.parse import parse_qs, urlparse

from src.purchase_links import build_purchase_links


def test_purchase_links_cover_chinese_marketplaces_and_use_isbn() -> None:
    links = build_purchase_links("具身心智：认知科学和人类经验", "978-7-308-07265-6")

    assert [link.platform for link in links] == ["京东", "当当", "淘宝", "拼多多"]
    assert all(link.url.startswith("https://") for link in links)
    for link in links:
        params = parse_qs(urlparse(link.url).query)
        query = (params.get("keyword") or params.get("key") or params.get("q") or params.get("search_key"))[0]
        assert "9787308072656" in query
        assert "具身心智" in query
        assert "官方旗舰店" in query


def test_purchase_links_encode_title_and_work_without_isbn() -> None:
    links = build_purchase_links("A&B / 中文版", None)

    assert len(links) == 4
    assert all("A%26B" in link.url for link in links)
    assert all("None" not in link.url for link in links)
