from scrapy.http import Request, TextResponse

from src.application.parsers.listings_parser import ListingParser


def test_item_attribute_selector_reads_source_listing_id():
    parser = ListingParser(
        source="batdongsan",
        selectors={
            "item": "div.js__card-listing",
            "url": "a.js__product-link-for-product-id::attr(href)",
            "source_listing_id": "::attr(prid)",
            "title": ".js__card-title::text",
        },
        allowed_domains=["batdongsan.com.vn"],
    )
    response = TextResponse(
        url="https://batdongsan.com.vn/nha-dat-ban",
        body=(
            b'<div class="js__card-listing" prid="46381984">'
            b'<a class="js__product-link-for-product-id" '
            b'href="/listing-pr46381984">Listing</a>'
            b"</div>"
        ),
        encoding="utf-8",
        request=Request(url="https://batdongsan.com.vn/nha-dat-ban"),
    )

    listings, stats = parser.parse_with_stats(response)

    assert stats.parsed == 1
    assert listings[0].source_listing_id == "46381984"
    assert listings[0].listing_key == "batdongsan:46381984"
