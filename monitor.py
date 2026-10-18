#!/usr/bin/env python3
"""Rohlík × Košík – public sale-page price watch (unofficial).

No credentials. Reads visible public listing cards with Playwright. Does NOT
claim catalog completeness, personalized prices or stock. Failures are surfaced.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
DATA = ROOT / "docs" / "data"
PRODUCT_URLS = {
    "Rohlík": re.compile(r"^/\d{5,}(?:-[a-z0-9-]+)?/?$", re.I),
    "Košík": re.compile(r"^/p\d+(?:-[a-z0-9-]+)?/?$", re.I),
}
PRICE_DECIMAL = re.compile(r"(?<!\d)(\d{1,4})[,.](\d{2})(?!\d)")
PRICE_SPLIT = re.compile(r"(?<!\d)(\d{1,4})[ \u00a0\u202f\n\r]+(\d{2})(?!\d)")
SALE_PCT = re.compile(r"(?<!\w)[−\-]\s*(\d{1,2})\s*%")
SIZE_PATTERN = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|ks)\b", re.I)

@dataclass
class Offer:
    shop: str
    name: str
    url: str
    price: float
    discount_pct: int
    old_price: float | None
    brand: str
    favorite: bool
    quantity: str
    terms: str
    comparable_group: str = ""
    other_shop_price: float | None = None
    other_shop_url: str = ""
    other_shop: str = ""
    category: str = ""
    rule_id: str = ""
    note: str = ""


def normalized(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("×", "x").replace("&", " a ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def brand_of(name: str, brands: list[dict]) -> str:
    # Anchored: avoids matching brand names inside unrelated words.
    check = " " + normalized(name) + " "
    for b in brands:
        for alias in b["aliases"]:
            key = normalized(alias)
            if key and (" " + key + " ") in check:
                return b["name"]
    return ""



def term_matches(n: str, expression: str) -> bool:
    """Case-/diacritic-insensitive full word/phrase, with terminal * prefix notation.

    This avoids accidental 'Axe' matches in unrelated words and allows Czech
    grammatical variants like šunk* / paprik* without unrestricted substrings.
    """
    prefix = expression.endswith("*")
    term = normalized(expression[:-1] if prefix else expression)
    if not term:
        return False
    if prefix:
        return re.search(r"(?<![a-z0-9])"+re.escape(term)+r"[a-z0-9]*", n) is not None
    return " " + term + " " in " " + n + " "



# These groups contain only unprocessed, fresh whole fruit and vegetables.
# Matching "banana" or "raspberry" anywhere in a title is NOT enough:
# that would incorrectly classify yogurt, supplements, beverages and snacks.
FRESH_PRODUCE_WORDS = {
    "W037": ("avokado", "avokada"),
    "W038": ("banan", "banany", "bananu"),
    "W039": ("boruvka", "boruvky", "boruvek"),
    "W040": ("malina", "maliny", "malin"),
    "W041": ("citron", "citrony", "citronu"),
    "W042": ("hrozny", "hroznu", "hroznove vino", "hroznoveho vina"),
    "W043": ("okurka", "okurky", "okurek", "okurku"),
    "W044": ("rajce", "rajcata", "rajcat"),
    "W045": ("rajce", "rajcata", "rajcat"),
    "W046": ("mrkev", "mrkve", "mrkvicka", "mrkvicky", "karotka", "karotky", "karotek"),
    "W047": ("paprika", "papriky", "papriku", "paprik"),
}

# Legitimate descriptors before the commodity, such as "BIO mrkev",
# "České čerstvé borůvky" or "Chiquita banány". This deliberately errs
# on the side of omitting ambiguous listings rather than false alerts.
FRESH_PRODUCE_PREFIX = frozenset("""
    bio cerstve cerstva cerstvy cerstvych cerstvi ceske ceska cesky
    ceskych farmarske farmarska farmarsky farmarskych vyberove vyberova
    premium organic eko lokalni velke male sladke sladka sladka
    spanelske spanelska italske italska belgicke peruanske
    chiquita bonita dole del monte farm fresh nature cherry mini
    koktejlova koktejlove baby volne balene balena baleny
""".split())

# Whole fresh produce only: never the fruit-flavoured version of another item,
# juice, sweet, dairy product, ready meal, preserved/dried/frozen produce,
# cosmetics, supplements, etc. Patterns are applied to complete word stems.
NON_FRESH_PRODUCE = (
    "actimel*", "magnesia", "dr max", "vitamin*", "tablet*", "horcik*",
    "dopln*", "probiot*", "napoj*", "limonad*", "dzus*", "nektar*",
    "smoothie", "sirup*", "stavy", "stava", "stavu", "stav", "caj", "caje",
    "jogurt*", "kefir*", "mleko", "mlecny", "mlecna", "mlecne",
    "mozzarella", "syr", "syry", "toast*", "sendvic*", "bageta",
    "dezert*", "pudink*", "krem*", "koktejl", "koktejly", "zmrzlin*",
    "pecivo", "kolac*", "buchta", "bucht*", "rohlik", "tycink*",
    "susen*", "susenk*", "lyofiliz*", "mrazen*", "zmrazen*",
    "chips*", "cokolad*", "polev*", "bonbon*", "cukrovink*", "cereali*",
    "marmelad*", "dzem*", "protlak*", "kecup*", "kase", "kasi",
    "pyre", "presnidavk*", "prichut*", "aroma*", "ochucen*", "esence",
    "ravioli", "testovin*", "rizoto", "pizza", "omack*", "polevk*",
    "hotove jidlo", "hotov*", "pomazank*", "koreni", "mlet*",
    "konzerv*", "sterilovan*", "nakladan*", "zavaren*", "kysel*", "kandovan*", "plnen*",
    "fermentovan*", "grilovan*", "pecen*", "marinovan*", "olej*",
    "protein*", "kapsl*", "sampon*", "kosmetik*", "maska", "gel",
    "cistic*", "mydlo", "vune", "sprej", "doplnek stravy",
)


def is_fresh_produce_name(name: str, rule: dict) -> bool:
    """True only if the main product is fresh whole fruit/vegetables.

    Without a reliable shop-category field, ambiguous offers are omitted.
    Avoid inferring the commodity from an ingredient/flavour anywhere in name.
    """
    if rule.get("category") not in ("Ovoce", "Zelenina"):
        return True
    lexicon = FRESH_PRODUCE_WORDS.get(rule.get("id"), ())
    if not lexicon:
        return False  # Fail closed for new produce rules pending review.
    n = normalized(name)
    if any(term_matches(n, word) for word in NON_FRESH_PRODUCE):
        return False
    tokens = n.split()
    # Require a whole-word produce noun. Banana-flavoured adjectives such as
    # "banánové", "malinový" or "citronová" do not qualify.
    for commodity in lexicon:
        words = commodity.split()
        for i in range(len(tokens) - len(words) + 1):
            if tokens[i:i + len(words)] != words:
                continue
            # All words before the commodity must be known fresh-produce
            # descriptors (not "Actimel Kids ..." or "Dr.Max ...").
            if i <= 5 and all(w in FRESH_PRODUCE_PREFIX for w in tokens[:i]):
                return True
    return False


def scrub_historical_produce(config: dict) -> int:
    """Repair misleading fruit/vegetable entries from pre-v7 daily archives.

    Preserve genuine prices/history, removing only incorrectly classified
    produce rows. This is idempotent, so scheduled runs can invoke it safely.
    """
    history = DATA / "history"
    rules_by_id = {r["id"]: r for r in config.get("watch_rules", [])}
    removed_total = 0
    for path in sorted(history.glob("*.json")) if history.exists() else []:
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        offers = snapshot.get("offers")
        if not isinstance(offers, list):
            continue
        kept = []
        for offer in offers:
            if offer.get("category") not in ("Ovoce", "Zelenina"):
                kept.append(offer)
                continue
            rule = rules_by_id.get(offer.get("rule_id", ""))
            if not rule:
                rule = match_rules(offer.get("name", ""), config.get("watch_rules", []))
            if rule and rule.get("category") in ("Ovoce", "Zelenina") and is_fresh_produce_name(offer.get("name", ""), rule):
                kept.append(offer)
        removed = len(offers) - len(kept)
        if removed:
            snapshot["offers"] = kept
            kept_urls = {o["url"] for o in kept}
            snapshot["changes"] = [c for c in snapshot.get("changes", []) if c.get("url") in kept_urls]
            snapshot["produce_filter_repaired"] = True
            path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
            removed_total += removed
    return removed_total


def match_rules(name: str, rules: list[dict]) -> dict | None:
    n = normalized(name)
    matched = []
    # A name matching a known tracked brand should not be mistaken for a raw
    # vegetable/fruit just because it contains the same word (Jar Citron etc.).
    known_brands = {
        normalized(a) for r in rules for a in r.get('brand_aliases', [])
        if len(normalized(a)) > 3
    }
    has_brand = any(term_matches(n, a) for a in known_brands)
    for r in rules:
        if not r.get("enabled", True):
            continue
        if r.get("brand_aliases") and not any(term_matches(n, alias) for alias in r["brand_aliases"]):
            continue
        if has_brand and not r.get("brand_aliases") and r.get('category') in ('Ovoce', 'Zelenina'):
            continue
        if r.get("category") in ("Ovoce", "Zelenina") and not is_fresh_produce_name(name, r):
            continue
        if r.get("product_any") and not any(term_matches(n, term) for term in r["product_any"]):
            continue
        if any(term_matches(n, term) for term in r.get("exclude_any", [])):
            continue
        # For ties, more specific rules beat broad general ones.
        specificity = max((len(normalized(t.strip('*'))) for t in r.get('product_any', [])), default=0)
        matched.append((r.get("priority", 2), -int(bool(r.get('brand_aliases'))), -specificity, r))
    return min(matched, key=lambda x: (x[0], x[1], x[2]))[3] if matched else None


def favorite_match(name: str, url: str, favorites: list[dict]) -> bool:
    n = normalized(name)
    for f in favorites:
        if f.get("url") and f["url"].rstrip("/") == url.rstrip("/"):
            return True
        if f.get("keywords") and all(normalized(w) in n for w in f["keywords"]):
            return True
    return False


def parse_price(text: str) -> float | None:
    text = text.replace("\u202f", " ").replace("\u00a0", " ").strip()
    # Price text must be constrained to a price-bearing element or pre-title card prefix.
    matches = [m for rx in (PRICE_DECIMAL, PRICE_SPLIT) if (m := rx.search(text))]
    m = min(matches, key=lambda match: match.start()) if matches else None
    if m:
        val = float(f"{m.group(1)}.{m.group(2)}")
        return round(val, 2) if 0 < val < 100000 else None
    return None


def quantity_of(name: str, context: str) -> str:
    # Prefer product name, which distinguishes multipacks from single units.
    m = SIZE_PATTERN.search(name) or SIZE_PATTERN.search(context[:160])
    return (m.group(1).replace(",", ".") + " " + m.group(2).lower()) if m else ""


def parse_card(shop: str, row: dict, config: dict) -> Offer | None:
    url = row.get("url", "")
    if urlparse(url).netloc not in ("www.rohlik.cz", "rohlik.cz", "www.kosik.cz", "kosik.cz"):
        return None
    if not PRODUCT_URLS[shop].match(urlparse(url).path):
        return None
    name = re.sub(r"\s+", " ", row.get("name", "")).strip()
    if len(name) < 4 or len(name) > 180:
        return None
    brand = brand_of(name, config.get("brands", []))
    fav = favorite_match(name, url, config.get("favorites", []))
    matched_rule = match_rules(name, config["watch_rules"]) if config.get("watch_rules") else None
    if config.get("watch_rules") and not matched_rule and not fav:
        return None
    if not config.get("watch_rules") and not brand and not fav:
        return None
    if matched_rule and int(matched_rule.get("priority", 2)) == 1:
        fav = True
    snippet = row.get("card", "")[:850]
    # A visible sale percentage in the same product card is mandatory.
    m = SALE_PCT.search(snippet)
    if not m:
        return None
    discount = int(m.group(1))
    if discount < 1 or discount > 90:
        return None
    threshold = int(config.get("favorite_min_discount_pct", 5)) if fav else int(
        config.get("monitoring", {}).get("brand_min_discount_pct", 15))
    if not config.get("watch_rules") and not fav:
        threshold = next((int(b.get("min_discount_pct", 15)) for b in config["brands"] if b["name"] == brand), 15)
    if discount < threshold:
        return None
    conditional = re.search(r"od\s+(\d+)\s*ks", snippet, re.I)
    terms = f"množstevní akce (od {conditional.group(1)} ks)" if conditional else (
        "množstevní akce (podmínky ověřit)" if re.search(r"multikup|kup v[ií]c", snippet, re.I) else "akce")
    # If the page only exposes the price after a minimum quantity, treat this
    # offer as quantity-conditional, and never compare it as an ordinary price.
    candidate = row.get("current_price", "")
    price = parse_price(candidate) if candidate else None
    if price is None:
        # Card begins with price on Košík; Rohlík cards usually place 0 kusů first.
        prefix = snippet.split(name)[0]
        prefix = re.sub(r"\b0\s+kus[uů]\s+v\s+ko[sš][ií]ku\b", "", prefix, flags=re.I)
        price = parse_price(prefix)
    if price is None:
        return None  # Never fabricate a price.
    old_price = parse_price(row.get("old_price", "")) if row.get("old_price") else None
    # Cross-check an explicit old price if available; allow rounding differences.
    if old_price is not None:
        if old_price <= price:
            return None
        # Reject inconsistent cards rather than publish likely misparsed prices.
        observed_discount = (1 - price / old_price) * 100
        if abs(observed_discount - discount) > 7:
            return None
    category = matched_rule.get("category", "") if matched_rule else ""
    label = matched_rule.get("label", "") if matched_rule else ""
    return Offer(shop, name, url, price, discount, old_price, brand or label or "Oblíbené", fav,
                 quantity_of(name, snippet), terms,
                 category=category, rule_id=matched_rule.get("id", "") if matched_rule else "",
                 note=matched_rule.get("note", "") if matched_rule else "")


def classify_rows(shop: str, rows: list[dict], config: dict) -> list[Offer]:
    offers = {}
    for r in rows:
        o = parse_card(shop, r, config)
        if o and (o.url not in offers or (o.favorite and not offers[o.url].favorite)):
            offers[o.url] = o
    return list(offers.values())


# JavaScript executes in page after rendering; deliberately avoids hidden API endpoints.
EXTRACT_JS = r"""() => {
  const hostname = location.hostname;
  const rx = hostname.includes('rohlik') ? /^\/\d{5,}(?:-[\w-]+)?\/?$/i : /^\/p\d+(?:-[\w-]+)?\/?$/i;
  const roots = [...document.querySelectorAll('a[href]')].filter(a => {
    try { const u=new URL(a.href); return u.hostname===hostname && rx.test(u.pathname); }
    catch { return false; }
  });
  const items = [];
  for (const a of roots) {
    let e=a, selected=null;
    for (let i=0;i<7 && e;i++,e=e.parentElement) {
      const t=(e.innerText||'').trim();
      if (t.length>15 && t.length<800 && /[-−]\s*\d{1,2}\s*%/.test(t)) { selected=e; break; }
    }
    if (!selected) continue;
    const card=(selected.innerText||'').trim();
    const imgAlt=(a.querySelector('img')?.alt || selected.querySelector('img')?.alt || '').trim();
    const title=(a.getAttribute('title')||a.getAttribute('aria-label')||'').trim();
    const raw=(a.innerText||'').trim();
    // Prefer image alt / semantic label. Anchor text may contain price and a
    // different item in a multi-product grid, so never treat it as a title if
    // it contains Kč, discount percentages or basket UI elements.
    const titleCandidate=[imgAlt,title,raw].find(t=>t.length>4 && t.length<180
      && !/(?:Kč|kusů v košíku|[-−]\s*\d{1,2}\s*%)/i.test(t))||'';
    let name=titleCandidate;
    if (!name) {
      const near=selected.querySelector('a[href="'+a.getAttribute('href')+'"]');
      name=(near?.getAttribute('title')||near?.getAttribute('aria-label')||'').trim();
    }
    if (!name) continue;
    // Where semantic price elements exist, use them; else Python parses card prefix.
    const old=selected.querySelector('del, s, [class*="originalPrice"], [class*="oldPrice"]');
    let current='';
    const priceElt=selected.querySelector('[data-testid*="price"], [class*="currentPrice"], [class*="Price_current"], [class*="salePrice"]');
    if (priceElt) current=(priceElt.innerText||'').trim().slice(0,35);
    items.push({url:a.href,name,card,current_price:current,old_price:(old?.innerText||'').trim()});
  }
  return items;
}"""


def fetch_shop(shop: str, url: str, max_items: int) -> tuple[list[dict], str]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(locale="cs-CZ", timezone_id="Europe/Prague", viewport={"width": 1365, "height": 1000},
                                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/133.0 Safari/537.36")
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            if resp is None or resp.status >= 400:
                return [], f"HTTP {resp.status if resp else 'bez odpovědi'}"
            page.wait_for_timeout(2500)
            try:
                page.get_by_role("button", name=re.compile("Přijmout|Souhlasím|Povolit vše", re.I)).first.click(timeout=1200)
            except Exception:
                pass
            all_rows: dict[str, dict] = {}
            for _ in range(9):
                rows = page.evaluate(EXTRACT_JS)
                for row in rows:
                    all_rows[row["url"]] = row
                if len(all_rows) >= max_items:
                    break
                page.mouse.wheel(0, 2400)
                page.wait_for_timeout(850)
                # Many sites paginate or virtualize: this is a sampled subset,
                # explicitly NOT a claim of all sale items.
            return list(all_rows.values())[:max_items], "ok" if all_rows else "Nenalezeny produktové karty; pravděpodobně změna webu nebo blokování"
        finally:
            browser.close()


def comparison_key(name: str, quantity: str) -> str:
    """Conservative match; manual aliases override automatically."""
    n = normalized(name)
    # Normalizing ampersands and punctuation is okay; do not conflate 'zero' or packs.
    return f"{n} | {normalized(quantity)}"


def add_comparisons(offers: list[Offer], pairs: list[dict]) -> None:
    manual = {}
    for pair in pairs:
        key = pair.get("id") or "manual"
        for url in (pair.get("rohlik_url"), pair.get("kosik_url")):
            if url:
                manual[url.rstrip("/")] = "manual:" + key
    for o in offers:
        o.comparable_group = manual.get(o.url.rstrip("/"), "auto:" + comparison_key(o.name, o.quantity))
    groups = defaultdict(list)
    for o in offers:
        groups[o.comparable_group].append(o)
    for group in groups.values():
        shops = {o.shop for o in group}
        if len(group) != 2 or len(shops) != 2:
            continue  # Never compare ambiguous or non-identical items.
        a, b = group
        if a.terms != b.terms:
            continue  # Conditional prices not equivalent to ordinary discounts.
        a.other_shop_price, a.other_shop_url, a.other_shop = b.price, b.url, b.shop
        b.other_shop_price, b.other_shop_url, b.other_shop = a.price, a.url, a.shop


def demo_rows():
    return {
        "Rohlík": [
            dict(name="LE&CO Šunka od kosti 100 g", url="https://www.rohlik.cz/1234567-sunka", card="0 kusů v košíku\n34,90 Kč 44,90 Kč -22 % do 20.10. LE&CO Šunka od kosti 100 g", current_price="34,90 Kč", old_price="44,90 Kč"),
            dict(name="Coca-Cola Original 2 l", url="https://www.rohlik.cz/1234568-cola", card="0 kusů v košíku\n39,90 Kč 49,90 Kč -20 % Coca-Cola Original 2 l", current_price="39,90 Kč", old_price="49,90 Kč")
        ],
        "Košík": [
            dict(name="Coca-Cola Original 2 l", url="https://www.kosik.cz/p12345-cola", card="36 90 49,90 -26 % do 20.10. Coca-Cola Original 2 l", current_price="36,90 Kč", old_price="49,90 Kč"),
            dict(name="Aquila První voda 6x1,5 l", url="https://www.kosik.cz/p12346-aquila", card="89 90 119,90 -25 % do 20.10. Aquila První voda 6x1,5 l", current_price="89,90 Kč", old_price="119,90 Kč")
        ]
    }


def read_previous() -> dict:
    p = DATA / "latest.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError):
        return {}


def compare_changes(current: list[Offer], previous: dict) -> list[dict]:
    old_by_url = {x["url"]: x for x in previous.get("offers", [])}
    changes = []
    for offer in current:
        prior = old_by_url.get(offer.url)
        if not prior or prior.get("price") is None:
            changes.append({"url": offer.url, "kind": "newly_observed", "price": offer.price})
        elif offer.price < float(prior["price"]) - 0.005:
            changes.append({"url": offer.url, "kind": "price_dropped", "price": offer.price,
                            "previous_price": prior["price"]})
    return changes


def build_report(snapshot: dict) -> str:
    offers = [Offer(**x) for x in snapshot["offers"]]
    offers.sort(key=lambda o: (not o.favorite, -o.discount_pct, o.brand, o.name))
    lines = [f"ROHLÍK × KOŠÍK | {snapshot['date']} | poslední kontrola: {snapshot['checked_at']}",
             "VEŘEJNÉ AKCE – pouze položky skutečně nalezené při kontrole, nikoli kompletní katalog.",
             f"Doručovací oblast: PSČ {snapshot.get('delivery', {}).get('postal_code', 'neuvedeno')} (referenční požadavek, nikoli automaticky ověřená lokální cena).",
             "Bez potvrzené volby oblasti v e-shopu: ceny a dostupnost se mohou lišit podle doručovací adresy / členství.",
             "STAV ZDROJŮ: " + "; ".join(f"{s}: {v['status']} ({v['cards']} karet)" for s, v in snapshot["sources"].items()),
             f"Nalezeno {len(offers)} sledovaných zlevněných položek; nově zaznamenané / zlevněné: {len(snapshot['changes'])}.",
             "OBLÍBENÉ PRODUKTY A ZNAČKY:"]
    if not offers:
        lines.append("Žádná ověřená nabídka v dostupném vzorku; neznamená to, že žádná sleva neexistuje.")
    for o in offers[:80]:
        comp = f" | druhý obchod: {o.other_shop} {o.other_shop_price:.2f} Kč" if o.other_shop_price is not None else " | bez ověřeného páru"
        lines.append(f"{'★ ' if o.favorite else ''}{o.category or o.brand} | {o.shop} | {o.name} | {o.price:.2f} Kč | -{o.discount_pct}% | {o.terms}{comp} | {o.url}" + (f" | POZN.: {o.note}" if o.note else ""))
    if len(offers) > 80:
        lines.append(f"Dalších {len(offers) - 80} položek pouze na webovém dashboardu.")
    lines.extend(["Zdroje:"] + [f"{k}: {v}" for k, v in snapshot["source_urls"].items()])
    if snapshot.get("demo"):
        lines.insert(0, "*** DEMO DATA – NESKUTEČNÉ CENY ***")
    return "\n".join(lines) + "\n"


def write_snapshot(snapshot: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "history").mkdir(exist_ok=True)
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
    (DATA / "latest.json").write_text(payload, encoding="utf-8")
    (DATA / "history" / (snapshot["date"] + ".json")).write_text(payload, encoding="utf-8")
    (DATA / "report.txt").write_text(build_report(snapshot), encoding="utf-8")
    # Basic static HTML usable as text input to ChatGPT; escape all external data.
    (ROOT / "docs" / "report.html").write_text(
        '<!doctype html><html lang="cs"><meta charset="utf-8"><title>Denní cenový report</title>'
        '<meta name="robots" content="noindex"><body><h1>Rohlík × Košík – denní report</h1><pre>'
        + html.escape(build_report(snapshot)) + '</pre></body></html>', encoding="utf-8")
    index = DATA / "index.json"
    try:
        dates = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    except ValueError:
        dates = []
    dates = sorted(set(dates + [snapshot["date"]]), reverse=True)[:120]
    index.write_text(json.dumps(dates, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="Generate synthetic demo results (NOT real prices)")
    ap.add_argument("--config", type=Path, default=CONFIG)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    now = dt.datetime.now(ZoneInfo(cfg.get("timezone", "Europe/Prague")))
    rows_by_shop = demo_rows() if args.demo else {}
    statuses = {}
    for shop, url in cfg["sources"].items():
        if not args.demo:
            try:
                rows, status = fetch_shop(shop, url, int(cfg.get("max_items_per_store", 400)))
            except Exception as exc:
                rows, status = [], f"CHYBA: {type(exc).__name__}: {str(exc)[:150]}"
            rows_by_shop[shop] = rows
        else:
            status = "DEMO – syntetická data"
            rows = rows_by_shop[shop]
        statuses[shop] = {"status": status, "cards": len(rows)}
    previous = read_previous()
    offers = []
    for shop, rows in rows_by_shop.items():
        offers.extend(classify_rows(shop, rows, cfg))
    # Repair historical false positives as well, so past days do not keep
    # listing juice/yogurt/sweets as fresh fruit or vegetables.
    if not args.demo:
        scrub_historical_produce(cfg)
    add_comparisons(offers, cfg.get("canonical_pairs", []))
    offers.sort(key=lambda o: (not o.favorite, -o.discount_pct, o.brand, o.name))
    snapshot = {"date": now.date().isoformat(), "checked_at": now.isoformat(timespec="minutes"),
                "sources": statuses, "source_urls": cfg["sources"],
                "delivery": cfg.get("delivery", {}), "postcode_specific_prices_verified": False,
                "offers": [asdict(o) for o in offers],
                "changes": compare_changes(offers, previous),
                "demo": args.demo,
                "disclaimer": "Veřejný vzorek, ne úplný katalog; PSČ je zadáno pouze jako preference (neověřené lokální ceny a dostupnost); množstevní slevy podmíněné."}
    write_snapshot(snapshot)
    print(f"{snapshot['checked_at']} | {len(offers)} nabídek | {statuses}")
    # Exit nonzero if ALL sources fail; do NOT present this as 'no sales'.
    return 0 if args.demo or any(v["status"] == "ok" for v in statuses.values()) else 2


if __name__ == "__main__":
    sys.exit(main())
