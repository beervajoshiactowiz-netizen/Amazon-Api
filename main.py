from fastapi import FastAPI, Query, HTTPException
from curl_cffi import requests
from lxml import html
from urllib.parse import quote_plus

app = FastAPI(title="Amazon API")


headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'device-memory': '8',
    'downlink': '9.3',
    'dpr': '1.5',
    'ect': '4g',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.amazon.com/',
    'rtt': '0',
    'sec-ch-device-memory': '8',
    'sec-ch-dpr': '1.5',
    'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-full-version-list': '"Google Chrome";v="147.0.7727.56", "Not.A/Brand";v="8.0.0.0", "Chromium";v="147.0.7727.56"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"19.0.0"',
    'sec-ch-viewport-width': '1280',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
    'viewport-width': '1280',
    'x-requested-with': 'XMLHttpRequest',
    # 'cookie': 'aws-waf-token=5d784c74-957b-4017-bd87-3f50d86e026e:EQoAgWEtbh0FAAAA:7ngYgAjO3johDQ5UMwdxiq3DaZ/1FxuomydwDUFzFzAy/b0lt/BAB1C2hpx3fw8KE0j75mlxiaZK7428DDXHufM9u3ADCkpdNQ+ku6bl3hWM7RkNWO802Bv3AbmA3GzQXCY6JPo9tV7P8Oc56qRcQrYa03jikv76XIncCjQXem9Rc3f7iEFiPtxwfkqz2XDcuQ==; session-id=131-3059121-0726953; session-id-time=2082787201l; i18n-prefs=USD; lc-main=en_US; ubid-main=131-5109861-9530515; av-timezone=Asia/Calcutta; skin=noskin; session-token=hbyGnp9B7Qr0wfMTpUdQ5RL2zSbXx6S0D5ziCwwzeO3uftz980cxa0jBC5t3syRRBwuj4vuo44FK/LLPm3E0XVfJDSQe5/jtGVHYrRDT3smCVeOHgBqfziKtfjnbBl6bbdkxJdMK3rs/Bb/Ld7kyspp3W5+PrmOfywTsgXIcCHkV9CDg6nE0QfrkcGuyaK+4zKkWM+IEaLC/DyLEqbP2f02gJz7hiTNx; csm-hit=tb:TN3KMD95ESZ81N4YPSSX+s-8VBKCA4ZBTY37GDVH8ZS|1776324060114&t:1776324060114&adb:adblk_no; rxc=AGGoWSRtny4N+n4snuE',
}

@app.get("/")
def home():
    return {"message": "Amazon"}


@app.get("/suggest")
def get_suggestions(q: str = Query(...)):
    try:
        params = {
            'limit': '11',
            'prefix': q,
            'suggestion-type': [
                'WIDGET',
                'KEYWORD',
            ],
            'page-type': 'Gateway',
            'alias': 'aps',
            'site-variant': 'desktop',
            'version': '3',
            'event': 'onkeypress',
            'wc': '',
            'lop': 'en_US',
            'last-prefix': 'lapto',
            'avg-ks-time': '633',
            'fb': '1',
            'predicted_text_accepted': '',
            'estoken': '',
            'session-id': '131-3059121-0726953',
            'request-id': '8VBKCA4ZBTY37GDVH8ZS',
            'mid': 'ATVPDKIKX0DER',
            'plain-mid': '1',
            'client-info': 'search-ui',
        }
        res = requests.get('https://www.amazon.com/suggestions', params=params, headers=headers, impersonate="chrome124")
        data = res.json()

        suggestion = []

        for item in data.get("suggestions", []):
            suggestion.append({
                "value": item.get("value"),
                "refTag": item.get("refTag")
            })

        return {
            "search_keyword": q,
            "count": len(suggestion),
            "results": suggestion
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_products(q: str = Query(...),reftag: str = Query(...)):
    try:
        url = f"https://www.amazon.com/s?k={quote_plus(q)}&ref={reftag}"

        res = requests.get(
            url,
            headers=headers,
            timeout=15,
            impersonate="chrome124"
        )

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
            "reftag":reftag,
            "count": len(products),
            "products": products
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/product/{asin}")
def get_product_details(asin: str):
    try:
        url = f"https://www.amazon.com/dp/{asin}"

        res = requests.get(url, headers=headers, timeout=20)

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
            "about": [x.strip() for x in bullets if x.strip()]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
