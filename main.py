from fastapi import FastAPI, Query, HTTPException
from curl_cffi import requests
from lxml import html
from urllib.parse import quote_plus

app = FastAPI(title="Amazon Search API")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}


@app.get("/")
def home():
    return {"message": "Amazon API"}


@app.get("/suggest")
def get_suggestions(q: str = Query(...)):
    try:
        url = (
            f"https://www.amazon.com/suggestions?"
            f"limit=11"
            f"&prefix={quote_plus(q)}"
            f"&suggestion-type=WIDGET"
            f"&suggestion-type=KEYWORD"
            f"&page-type=Gateway"
            f"&alias=aps"
            f"&site-variant=desktop"
            f"&version=3"
            f"&event=onkeypress"
            f"&lop=en_US"
            f"&client-info=search-ui"
        )

        res = requests.get(url, headers=HEADERS, timeout=15)
        data = res.json()

        suggestions = []

        for item in data.get("suggestions", []):
            suggestions.append({
                "value": item.get("value"),
                "refTag": item.get("refTag")
            })

        return {
            "search_keyword": q,
            "count": len(suggestions),
            "results": suggestions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_products(
    q: str = Query(...),
    page: int = Query(...)
):
    try:
        url = f"https://www.amazon.com/s?k={quote_plus(q)}&page={page}"

        res = requests.get(url, headers=HEADERS, timeout=20)

        tree = html.fromstring(res.text)

        cards = tree.xpath('//div[@data-component-type="s-search-result"]')

        products = []

        for card in cards:
            title = card.xpath('.//h2//span/text()')
            asin = card.xpath('./@data-asin')

            price_whole = card.xpath('.//span[@class="a-price-whole"]/text()')
            price_fraction = card.xpath('.//span[@class="a-price-fraction"]/text()')

            rating = card.xpath('.//span[contains(@class,"a-icon-alt")]/text()')

            products.append({
                "asin": asin[0] if asin else None,
                "title": title[0].strip() if title else None,
                "price": (
                    f"{price_whole[0]}{price_fraction[0]}"
                    if price_whole and price_fraction else None
                ),
                "rating": rating[0] if rating else None
            })

        return {
            "query": q,
            "page": page,
            "count": len(products),
            "products": products
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/product/{asin}")
def get_product_details(asin: str):
    try:
        url = f"https://www.amazon.com/dp/{asin}"

        res = requests.get(url, headers=HEADERS, timeout=20)

        tree = html.fromstring(res.text)

        title = tree.xpath('//span[@id="productTitle"]/text()')

        price_whole = tree.xpath('//span[@class="a-price-whole"]/text()')
        price_fraction = tree.xpath('//span[@class="a-price-fraction"]/text()')

        rating = tree.xpath('//span[@id="acrPopover"]/@title')

        bullets = tree.xpath('//div[@id="feature-bullets"]//span/text()')

        return {
            "asin": asin,
            "title": title[0].strip() if title else None,
            "price": (
                f"{price_whole[0]}{price_fraction[0]}"
                if price_whole and price_fraction else None
            ),
            "rating": rating[0] if rating else None,
            "features": [x.strip() for x in bullets if x.strip()]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))