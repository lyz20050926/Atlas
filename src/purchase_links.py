from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class PurchaseLink:
    platform: str
    url: str


def build_purchase_links(title: str, isbn: str | None = None) -> list[PurchaseLink]:
    """Build non-affiliate marketplace searches for a specific book edition.

    ISBN is included whenever available because it is a stronger edition-level
    identifier than title alone. Seller identity, stock, and prices remain the
    marketplace's live responsibility and are never inferred by Atlas.
    """

    clean_title = " ".join(title.split())
    clean_isbn = "".join(character for character in (isbn or "") if character.isdigit() or character in "Xx")
    query_parts = [part for part in (clean_isbn, clean_title, "正版 官方旗舰店") if part]
    encoded_query = quote_plus(" ".join(query_parts))

    return [
        PurchaseLink("京东", f"https://search.jd.com/Search?keyword={encoded_query}&enc=utf-8"),
        PurchaseLink("当当", f"https://search.dangdang.com/?key={encoded_query}"),
        PurchaseLink("淘宝", f"https://s.taobao.com/search?q={encoded_query}"),
        PurchaseLink("拼多多", f"https://mobile.yangkeduo.com/search_result.html?search_key={encoded_query}"),
    ]
