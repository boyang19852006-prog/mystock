import requests, json, re, os, time
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup

# ========== 配置区 ==========
BASE_URL = "http://www.qiange99.com"
SEARCHMORE_URL = BASE_URL + "/site/price/searchmore"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.38",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

session = requests.Session()
session.headers.update(HEADERS)

# ========== 抓取函数 ==========
def fetch_all_products():
    all_products = []
    page = 1
    total = 9999

    while (page - 1) * 20 < total:
        payload = {"key": "", "cate": "", "instock": "0", "price": "0"}
        resp = session.post(f"{SEARCHMORE_URL}/{page}", data=payload, timeout=30)
        raw = resp.json()
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw

        html = data["html"]
        if page == 1:
            match = re.search(r'total\s*=\s*(\d+)', html)
            if match:
                total = int(match.group(1))

        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("li", class_="list-chanpin")
        if not items:
            break

        for item in items:
            try:
                name_tag = item.find("h4")
                if not name_tag:
                    continue
                name = name_tag.get_text(strip=True)

                stock_tag = item.find("p", class_="kucun")
                stock_text = stock_tag.get_text(strip=True) if stock_tag else "库存：暂缺"
                stock = stock_text.replace("库存：", "").strip()

                price_tag = item.find("span", class_="xianjia")
                price_text = price_tag.get_text(strip=True) if price_tag else "0"
                fan_price = float(re.search(r'[\d.]+', price_text).group())

                img_tag = item.find("img", class_="img-rounded")
                img_url = ""
                if img_tag:
                    img_url = img_tag.get("data") or img_tag.get("src", "")
                    if img_url.startswith("/"):
                        img_url = BASE_URL + img_url

                all_products.append({
                    "name": name,
                    "stock": stock,
                    "fan_price": fan_price,
                    "image": img_url
                })
            except:
                continue

        page += 1
        time.sleep(0.5)

    return all_products

# ========== 加价规则 ==========
def calc_sell_price(fan_price):
    if fan_price >= 1500:
        return None
    if fan_price < 90:
        return fan_price + 5
    if fan_price < 180:
        return fan_price + 10
    if fan_price < 290:
        return fan_price + 20
    if fan_price < 390:
        return fan_price + 26
    if fan_price < 500:
        return fan_price + 34
    if fan_price < 600:
        return fan_price + 40
    if fan_price < 700:
        return fan_price + 50
    return fan_price + 50 + ((fan_price - 600) // 100) * 10

# ========== 主流程 ==========
if __name__ == "__main__":
    print("正在抓取商品...")
    products = fetch_all_products()
    print(f"共抓取 {len(products)} 个商品")

    output = []
    os.makedirs("images", exist_ok=True)

    for p in products:
        sell_price = calc_sell_price(p["fan_price"])
        if sell_price is None:
            continue

                img_name = ""
        if p["image"]:
            try:
                img_name = f"img_{abs(hash(p['name']))}.jpg"
                img_path = f"images/{img_name}"
                if not os.path.exists(img_path):
                    r = session.get(p["image"], timeout=15)
                    if r.status_code == 200:
                        img = Image.open(BytesIO(r.content))
                        img = img.convert("RGB")
                        img.thumbnail((300, 300), Image.LANCZOS)
                        img.save(img_path, "JPEG", quality=75, optimize=True)
            except:
                img_name = ""

        output.append({
            "name": p["name"],
            "stock": p["stock"],
            "price": round(sell_price, 2),
            "image": f"images/{img_name}" if img_name else ""
        })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成，共 {len(output)} 个商品可供展示")
