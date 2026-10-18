"""Incremental *whole-catalog-search* watcher for Rohlík / Košík.

Finds products via the PUBLIC site search box across categories, irrespective
of whether the product is on sale. No private APIs, authentication, captcha
bypass, or claim that a retailer's entire catalogue was enumerated.

The planned queries cover every configured shopping rule at both stores. The
scan is split across recurring runs and persists per-query outcomes and the
last *observed* prices. A query returning zero rows is not a proof of absence.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

QUERY_BY_RULE = {
    'W001': ['kuřecí prsní řízky', 'kuřecí prsa'],
    'W002': ['kuřecí stehna', 'kuřecí paličky'],
    'W003': ['vepřová krkovice'],
    'W004': ['vepřová panenka'],
    'W005': ['hovězí svíčková'],
    'W037': ['avokádo'], 'W038': ['banány'],
    'W039': ['borůvky'], 'W040': ['maliny'],
    'W041': ['citrony'], 'W042': ['hroznové víno', 'hrozny'],
    'W043': ['okurky'], 'W044': ['rajčata'],
    'W045': ['cherry rajčata'], 'W046': ['mrkev'],
    'W047': ['papriky'], 'W051': ['kokosky'],
    'W053': ['Zewa toaletní papír', 'Zewa ubrousky'],
    'W074': ['kuchyňské papírové utěrky', 'papírové utěrky'],
    'W075': ['kapesníky box 3vrstvé', 'kapesníky v krabici'],
}
# Supplemental searches limit the risk of a brand-only query being truncated
# before the relevant type (e.g. other cosmetics from AXE / another Zewa line).
EXTRA_BRAND_TERMS = {
    'W006': ['LE CO šunka'], 'W027': ['Hellmann majonéza'],
    'W019': ['President plátkový sýr'],
    'W020': ['Smetanito'], 'W022': ['Lipno tavený sýr'],
    'W023': ['Král sýrů hermelín'],
    'W026': ['Galbani mozzarella'],
    'W028': ['Madeta máslo'],
    'W033': ['Aquila 1,5 l'], 'W034': ['Rajec 1,5 l'],
    'W035': ['Dobrá voda 1,5 l'],
    'W036': ['Coca-Cola Original 1,5 l', 'Coca-Cola Original 2 l'],
    'W052': ['Panzani těstoviny', 'Panzani rýže'],
    'W055': ['Axe deodorant', 'Axe sprchový gel'],
    'W056': ['Syoss Men Intense Power'],
    'W060': ['Wilkinson jednorázová holítka'],
    'W072': ['Jar citron'], 'W073': ['Zewa Deluxe Standard kapesníky'],
    'W074': ['Zewa papírové utěrky'],
    'W075': ['Zewa kapesníky box', 'papírové kapesníky box'],
}


def plan_queries(config: dict) -> list[dict]:
    """One search term may cover multiple rules; EVERY rule is represented."""
    dedup: dict[str, dict] = {}
    for rule in config.get('watch_rules', []):
        if rule.get('enabled') is False:
            continue
        rid = rule['id']
        queries = config.get('catalog_search',{}).get('queries_by_rule',{}).get(rid,QUERY_BY_RULE.get(rid))
        if queries is None:
            aliases = rule.get('brand_aliases', [])
            queries = [aliases[0]] if aliases else [rule['label']]
        queries = [*queries, *EXTRA_BRAND_TERMS.get(rid, [])]
        for term in queries:
            term = re.sub(r'\s+', ' ', term).strip()
            if not term:
                continue
            key = term.casefold()
            entry = dedup.setdefault(key, {'query': term, 'rule_ids': []})
            if rid not in entry['rule_ids']:
                entry['rule_ids'].append(rid)
    return list(dedup.values())


def plan_jobs(config: dict) -> list[dict]:
    """Interleave stores so each batch covers both, not just one retailer."""
    stores = tuple(config.get('sources', {}).keys())
    return [{'shop': shop, **plan} for q in plan_queries(config) for shop in stores for plan in [q]]


def job_key(job: dict) -> str:
    return f"{job['shop']}::{job['query'].casefold()}"


def choose_batch(jobs: list[dict], cursor: int, limit: int) -> tuple[list[dict], int]:
    if not jobs:
        return [], 0
    n = len(jobs)
    count = min(max(1, limit), n)
    chosen = [jobs[(cursor + i) % n] for i in range(count)]
    return chosen, (cursor + count) % n


# Executed against product cards in the *search results* — not the promotions
# page. A nearest-price-card check prevents grabbing neighbouring products.
SEARCH_EXTRACT_JS = r"""() => {
 const shop=location.hostname.includes('rohlik')?'Rohlík':'Košík';
 const pattern=shop==='Rohlík'?/^\/\d{5,}(?:-[\w-]+)?\/?$/i:/^\/p\d+(?:-[\w-]+)?\/?$/i;
 const nodes=[...document.querySelectorAll('a[href]')];
 const output=new Map();
 for(const a of nodes){
   let u;try{u=new URL(a.href)}catch(_){continue}
   if(u.hostname!==location.hostname||!pattern.test(u.pathname))continue;
   let card=null;
   for(let e=a,level=0;e&&level<7;e=e.parentElement,level++){
     const t=(e.innerText||'').trim();
     const links=[...e.querySelectorAll('a[href]')].filter(x=>{
       try{return pattern.test(new URL(x.href).pathname)}catch(_){return false}
     });
     const different=new Set(links.map(x=>new URL(x.href).pathname));
     if(different.size>1)continue;
     if(t.length>=6&&t.length<1100&&(/\d+[,. ]\d{2}\s*(?:Kč|CZK)/i.test(t)||/[-−]\s*\d{1,2}\s*%/.test(t))){card=e;break;}
   }
   if(!card)continue;
   const img=a.querySelector('img')||(card.querySelectorAll('a[href]').length<=2?card.querySelector('img'):null);
   const titleCandidates=[img?.alt,a.getAttribute('title'),a.getAttribute('aria-label'),a.innerText];
   let name=(titleCandidates.find(x=>x&&x.trim().length>=4&&x.trim().length<=185&&!/Kč|kusů v košíku|[-−]\s*\d{1,2}\s*%/i.test(x))||'').trim();
   name=name.replace(/^(?:zobrazit|otevřít)\s+detail\s+produktu\s*/i,'').trim();
   if(!name)continue;
   const price=card.querySelector('[data-testid*="price"], [class*="currentPrice"], [class*="salePrice"], [class*="Price_current"]');
   const old=card.querySelector('del, s, [class*="oldPrice"], [class*="originalPrice"]');
   const photo=img?.currentSrc||img?.getAttribute('data-src')||img?.getAttribute('src')||'';
   const item={url:u.href,name,card:(card.innerText||'').trim().slice(0,950),
       current_price:(price?.innerText||'').trim().slice(0,100),
       old_price:(old?.innerText||'').trim().slice(0,100),image_url:photo};
   const prev=output.get(u.pathname);
   if(!prev||(!prev.current_price&&item.current_price))output.set(u.pathname,item);
 }
 return [...output.values()];
}"""


def _get_search_field(page):
    for selector in ('input[type="search"]', 'input[role="searchbox"]',
                     'input[placeholder*="Hledat"]', 'input[placeholder*="Hledejte"]',
                     'input[aria-label*="Hledat"]', 'input[aria-label*="Hledejte"]'):
        loc = page.locator(selector).first
        try:
            if loc.count() and loc.is_visible():
                return loc
        except Exception:
            continue
    return None


def scan_single_query(page, base_url: str, query: str, *, max_cards: int = 300,
                      scrolls: int = 8) -> tuple[list[dict], str, str]:
    """Run visible store search; don't invent a URL or silently accept homepage cards."""
    try:
        landing=page.goto(base_url, wait_until='domcontentloaded', timeout=16000)
        if landing and landing.status in (403, 429):
            return [], 'rate_limited' if landing.status==429 else 'blocked', f'HTTP {landing.status}'
        if landing and landing.status >= 400:
            return [], 'error', f'Úvodní stránka HTTP {landing.status}'
        field = _get_search_field(page)
        if field is None:
            return [], 'search_unavailable', 'Nenalezeno veřejné vyhledávací pole'
        field.fill(query, timeout=4000)
        field.press('Enter', timeout=4000)
        page.wait_for_timeout(950)
        now_url = page.url
        # Search on some sites stays in the same route with an inline result pane;
        # do not assume those are actual search results without clear evidence.
        if now_url.rstrip('/') == base_url.rstrip('/'):
            value = (field.input_value() or '').strip()
            if value.casefold() != query.casefold():
                return [], 'search_unconfirmed', 'Vyhledávání nepotvrdilo zadaný dotaz'
            # Inline search results need a dedicated semantic results container.
            if not page.locator('[role="listbox"], [data-testid*="search-result"], [class*="search-result"]').count():
                return [], 'search_unconfirmed', 'Enter nepřešel na výsledky; nelze použít domácí nabídku'
        found = {}
        stagnant=0
        last_count=-1
        for _ in range(max(1,scrolls)):
            for row in page.evaluate(SEARCH_EXTRACT_JS):
                found[row['url']]=row
            if len(found)>=max_cards:
                return list(found.values())[:max_cards], 'partial_limit', f'Dosažen limit {max_cards} produktů'
            stagnant = (stagnant+1) if len(found)==last_count else 0
            last_count=len(found)
            if stagnant>=3:break
            clicked=False
            for selector in ('button:has-text("Načíst další")', 'button:has-text("Zobrazit další")'):
                try:
                    btn=page.locator(selector).first
                    if btn.count() and btn.is_visible():
                        btn.click(timeout=1300);clicked=True;break
                except Exception:
                    pass
            if not clicked:page.evaluate('window.scrollBy(0, Math.max(1000, innerHeight * 1.5))')
            page.wait_for_timeout(330)
        # Empty result is distinguishable from errors but NOT proof a product doesn't exist.
        return list(found.values()), 'ok' if found else 'no_cards', 'Veřejné výsledky vyhledávání; úplnost neověřena'
    except Exception as exc:
        msg=f'{type(exc).__name__}: {str(exc)[:160]}'
        if '429' in msg:return [], 'rate_limited', msg
        return [], 'error', msg


def playwright_search_batch(batch: list[dict], cfg: dict) -> dict[str, dict]:
    """One reusable browser; no logins, captcha circumvention or internal API."""
    from playwright.sync_api import sync_playwright
    results={}
    search_cfg=cfg.get('catalog_search', {})
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        pages={}
        blocked=set()
        try:
            for job in batch:
                key=job_key(job);shop=job['shop']
                if shop in blocked:
                    results[key]={'status':'skipped_rate_limit','items':[],'detail':'Další dotazy pozastaveny'}
                    continue
                if shop not in pages:
                    pages[shop]=browser.new_page(locale='cs-CZ',timezone_id='Europe/Prague',
                                                 viewport={'width':1366,'height':950})
                url='https://www.rohlik.cz/' if shop=='Rohlík' else 'https://www.kosik.cz/'
                rows,status,desc=scan_single_query(pages[shop],url,job['query'],
                    max_cards=int(search_cfg.get('max_cards_per_query',260)),
                    scrolls=int(search_cfg.get('scrolls_per_query',8)))
                results[key]={'status':status,'items':rows,'detail':desc}
                if status=='rate_limited':blocked.add(shop)
        finally:
            browser.close()
    return results


def _timestamp(t: str) -> dt.datetime | None:
    try:return dt.datetime.fromisoformat(t)
    except (ValueError, TypeError):return None


def _recent(t: str, now: dt.datetime, hours: float) -> bool:
    when=_timestamp(t)
    return bool(when and when.tzinfo and dt.timedelta(0)<=now-when<=dt.timedelta(hours=hours))


def row_to_product(shop: str, row: dict, cfg: dict, lib, observed_at: str) -> dict | None:
    """All relevant products, including products *without* discount badges."""
    url=row.get('url','')
    name=lib.clean_product_name(row.get('name',''))
    if not name or urlparse(url).netloc not in ('www.rohlik.cz','rohlik.cz','www.kosik.cz','kosik.cz'):
        return None
    if not lib.PRODUCT_URLS[shop].match(urlparse(url).path):return None
    match=lib.match_rules(name,cfg.get('watch_rules',[]))
    pinned=lib.favorite_match(name,url,cfg.get('favorites',[]))
    if not match and not pinned:return None
    # Exclude broad matches before looking for a discount. Product category
    # restrictions are the SAME as in the prior sale monitor.
    favorite=bool(match or pinned)
    snippet=row.get('card','')
    sale=lib.SALE_PCT.search(snippet)
    discount=int(sale.group(1)) if sale else 0
    parsed=None
    if sale:
        scratch=dict(cfg)
        scratch['favorite_min_discount_pct']=1
        mon=dict(cfg.get('monitoring',{}));mon['brand_min_discount_pct']=1
        scratch['monitoring']=mon
        parsed=lib.parse_card(shop,row,scratch)
    if parsed:
        price,old=parsed.price,parsed.old_price
        quantity=parsed.quantity;image=parsed.image_url
        note=parsed.note;terms=parsed.terms
    else:
        # When a discount badge exists but could not be verified, don't
        # silently treat its struck-through old price as a regular price.
        price=lib.parse_item_price(row.get('current_price','')) if not sale else None
        if price is None and not sale:
            prefix=snippet.split(name)[0]
            prefix=re.sub(r'\b0\s+kus[uů]\s+v\s+ko[sš][ií]ku\b','',prefix,flags=re.I)
            price=lib.parse_item_price(prefix)
        old=None
        quantity=lib.size_from_listing(name,row)
        image=lib.safe_image_url(row.get('image_url',''),url)
        note='Slevu nelze cenově ověřit' if sale else ''
        terms='neověřená akce' if sale else 'běžná nabídka'
    if isinstance(price,float) and not 0<price<100000:price=None
    return {
      'shop':shop, 'name':name,'url':url.split('?')[0],
      'price':price,'discount_pct':discount if parsed else 0,
      'old_price':old,'brand':lib.brand_of(name,cfg.get('brands',[])) or (match or {}).get('label','Oblíbené'),
      'favorite':favorite,'quantity':quantity,'terms':terms,
      'category':(match or {}).get('category',''),'rule_id':(match or {}).get('id',''),
      'note':note,'image_url':image,'checked_at':observed_at,
      'price_verified':price is not None, 'discount_verified':parsed is not None,
      'discount_candidate_pct':discount if sale else 0,
      'unit_price':None,'unit_label':'','other_shop_price':None,
      'other_shop':'','other_shop_url':'','comparable_group':'',
    }


def _offer_from_product(item: dict, lib):
    if not (item.get('price_verified') and item.get('discount_verified')):
        return None
    fields=lib.Offer.__dataclass_fields__
    kwargs={k:v for k,v in item.items() if k in fields}
    kwargs.setdefault('detail_source','listing')
    offer=lib.Offer(**kwargs)
    lib.set_unit_price(offer)
    return offer


def process_incremental(cfg: dict, now: dt.datetime, state: dict, jobs: list[dict],
                        batch: list[dict], results: dict, lib) -> tuple[dict, dict]:
    """Pure update, used by production and fixture tests."""
    state=copy.deepcopy(state) if isinstance(state,dict) else {}
    state.setdefault('items',{});state.setdefault('queries',{})
    seen_in_batch=set();accepted=0;failures=0
    at=now.isoformat(timespec='minutes')
    for job in batch:
        key=job_key(job)
        res=results.get(key,{'status':'error','items':[],'detail':'Bez odpovědi'})
        status=res.get('status','error')
        rows=res.get('items',[])
        if status not in ('ok','no_cards','partial_limit'):
            failures+=1
        if status in ('ok','partial_limit'):
            for row in rows:
                product=row_to_product(job['shop'],row,cfg,lib,at)
                if not product:continue
                key_item=product['url']
                existing=state['items'].get(key_item,{})
                # Keep a known cached verified image when the current listing lacks one.
                if not product['image_url'] and existing.get('image_url'):
                    product['image_url']=existing['image_url']
                state['items'][key_item]=product
                accepted+=1;seen_in_batch.add(key_item)
        state['queries'][key]={'checked_at':at,'status':status,'cards':len(rows),
                               'detail':str(res.get('detail',''))[:200],
                               'rule_ids':job['rule_ids']}
    retention_hours=int(cfg.get('catalog_search',{}).get('cache_retention_hours',72))
    state['items']={k:v for k,v in state['items'].items() if _recent(v.get('checked_at',''),now,retention_hours)}
    states=state['queries']
    recent_queries={k:v for k,v in states.items() if _recent(v.get('checked_at',''),now,24)}
    valid_status=('ok','partial_limit')  # 'no_cards' may mean blocked extraction, not full results
    successful_jobs=[j for j in jobs if (q:=recent_queries.get(job_key(j))) and q['status'] in valid_status]
    by_store={shop:{'planned':len([j for j in jobs if j['shop']==shop]),
                    'attempted_24h':len([j for j in jobs if j['shop']==shop and job_key(j) in recent_queries]),
                    'responded_24h':len([j for j in successful_jobs if j['shop']==shop])}
              for shop in cfg.get('sources',{})}
    rule_ids={r['id'] for r in cfg.get('watch_rules',[]) if r.get('enabled') is not False}
    scanned_rule_ids=set(x for j in successful_jobs for x in j['rule_ids'])
    failed_recent=[{'query':j['query'],'shop':j['shop'], 'status':recent_queries[job_key(j)]['status']}
                   for j in jobs if job_key(j) in recent_queries and recent_queries[job_key(j)]['status'] not in valid_status]
    coverage={'failed_queries_24h':len(failed_recent),'failed_query_examples':failed_recent[:12],
              'queries_planned':len(jobs),'queries_checked_24h':len(recent_queries),
              'queries_responded_24h':len(successful_jobs),
              'watch_rules_total':len(rule_ids),
              'watch_rules_with_search_24h':len(rule_ids & scanned_rule_ids),
              'by_store':by_store,'batch_queries':len(batch),
              'batch_product_rows_matched':accepted,'batch_errors':failures,
              'catalog_completeness_verified':False,
              'warning':'Vyhledávací dotazy napříč katalogy, nikoli úplný export obou e-shopů. Neúplnost, blokace a změny cen jsou možné.'}
    fresh_hours=float(cfg.get('catalog_search',{}).get('price_max_age_hours',18))
    catalog=[];offers=[]
    for item in state['items'].values():
        if not _recent(item.get('checked_at',''),now,fresh_hours):continue
        product=dict(item)
        catalog.append(product)
        if not product.get('discount_verified'):continue
        pct=product.get('discount_pct',0)
        threshold=int(cfg.get('favorite_min_discount_pct',5) if product.get('favorite') else cfg.get('monitoring',{}).get('brand_min_discount_pct',15))
        if pct>=threshold:
            offer=_offer_from_product(product,lib)
            if offer:offers.append(offer)
    # Only use verified cross-shop matches with explicit matching pack size,
    # including a non-discounted listing at the other store.
    compare_catalog_items(catalog,lib,cfg.get('canonical_pairs',[]))
    by_url={c['url']:c for c in catalog}
    for o in offers:
        c=by_url.get(o.url)
        if c and c.get('other_shop_price') is not None:
            o.other_shop_price=c['other_shop_price'];o.other_shop=c['other_shop'];o.other_shop_url=c['other_shop_url']
    state['last_scan']=at
    return state,{'catalog':catalog,'offers':offers,'coverage':coverage,'seen_batch':len(seen_in_batch)}


def compare_catalog_items(items: list[dict],lib,manual_pairs: list[dict] | None = None) -> None:
    manual_urls={}
    for pair in manual_pairs or []:
        for key in ('rohlik_url','kosik_url'):
            if pair.get(key):manual_urls[pair[key].split('?')[0].rstrip('/')]=('manual',pair.get('id',''),lib.normalized(pair.get('size','')))
    groups={}
    for item in items:
        if item.get('price') is None or not item.get('quantity') or 'množstevní' in (item.get('terms') or ''):continue
        name=lib.normalized(item['name'])
        size=lib.normalized(item['quantity'])
        key=manual_urls.get(item['url'].rstrip('/'))
        if key:
            # A manual pairing still needs both verified and matching sizes.
            if key[2] and size!=key[2]:continue
            groups.setdefault(key,[]).append(item)
        else:
            groups.setdefault(('auto',name,size),[]).append(item)
    for group in groups.values():
        if len(group)!=2 or group[0]['shop']==group[1]['shop']:continue
        a,b=group
        a['other_shop_price']=b['price'];b['other_shop_price']=a['price']
        a['other_shop']=b['shop'];b['other_shop']=a['shop']
        a['other_shop_url']=b['url'];b['other_shop_url']=a['url']


def run_catalog_monitor(cfg: dict, lib, *, demo: bool = False) -> int:
    now=dt.datetime.now(dt.timezone.utc).astimezone(lib.ZoneInfo(cfg.get('timezone','Europe/Prague')))
    jobs=plan_jobs(cfg)
    state_file=lib.DATA/'catalog_state.json'
    try:state=json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
    except (ValueError,OSError):state={}
    # Config changes add/remove queries. Persist next cursor after every batch.
    batch,cursor=choose_batch(jobs,int(state.get('cursor',0)),int(cfg['catalog_search'].get('max_queries_per_run',46)))
    if demo:
        results={job_key(j):{'status':'no_cards','items':[],'detail':'DEMO bez živých dat'} for j in batch}
    else:
        results=playwright_search_batch(batch,cfg)
    updated,output=process_incremental(cfg,now,state,jobs,batch,results,lib)
    updated['cursor']=cursor
    lib.DATA.mkdir(parents=True,exist_ok=True)
    state_file.write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding='utf-8')
    previous=lib.read_previous()
    # Add photo/size to actual discounted offers, not all catalog items.
    enrich={'visited':0,'filled':0,'errors':0,'photos_cached':0}
    if not demo and output['offers']:
        try:enrich=lib.enrich_from_product_pages(output['offers'],cfg)
        except Exception as exc:enrich['error']=f'{type(exc).__name__}: {str(exc)[:100]}'
    # Keep the original public *sale-page* scan only as an explicitly marked
    # safety fallback if storefront search gave no usable response for a shop.
    # It never counts towards the whole-catalog query coverage.
    fallback={}
    for shop,stat in output['coverage']['by_store'].items():
        if stat['responded_24h'] or not cfg.get('catalog_search',{}).get('fallback_to_sales_page',True) or demo:
            continue
        try:
            rows,status,_=lib.fetch_shop(shop,cfg['sources'][shop],
                                         int(cfg.get('max_items_per_store',3500)),max_rounds=16)
            fallback[shop]={'status':status,'cards':len(rows)}
            existing={o.url for o in output['offers']}
            for o in lib.classify_rows(shop,rows,cfg):
                if o.url not in existing:
                    output['offers'].append(o);existing.add(o.url)
        except Exception as exc:
            fallback[shop]={'status':f'{type(exc).__name__}: {str(exc)[:110]}','cards':0}
    output['coverage']['sale_page_fallback']=fallback
    known_catalog_urls={c['url'] for c in output['catalog']}
    for offer in output['offers']:
        if offer.url not in known_catalog_urls:
            row={**asdict(offer),'checked_at':now.isoformat(timespec='minutes'),
                 'price_verified':True,'discount_verified':True,'source_kind':'action_page_fallback'}
            output['catalog'].append(row);known_catalog_urls.add(offer.url)
    offer_dicts=[asdict(o) for o in output['offers']]
    # Reuse verified detail-page improvements for the all-products table.
    offer_by_url={o['url']:o for o in offer_dicts}
    for item in output['catalog']:
        o=offer_by_url.get(item['url'])
        if o:
            for prop in ('quantity','unit_price','unit_label','image_url','other_shop_price','other_shop','other_shop_url'):
                item[prop]=o.get(prop,item.get(prop))
            existing=updated['items'].get(item['url'])
            if existing and item.get('image_url'):
                existing['image_url']=item['image_url']
                existing['quantity']=item.get('quantity') or existing.get('quantity','')
    # Save enriched images to persistent cache so subsequent scheduled runs
    # don't repeat 12 expensive detail visits for the same known photo.
    state_file.write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding='utf-8')
    coverage=output['coverage']
    (lib.DATA/'search_status.json').write_text(json.dumps({
        'checked_at':now.isoformat(timespec='minutes'),'coverage':coverage,
        'queries':updated.get('queries',{})},ensure_ascii=False,indent=2),encoding='utf-8')
    sources={shop:{'status': ('ok' if (b:=coverage['by_store'][shop])['responded_24h'] else
                     ('fallback_action_page' if fallback.get(shop,{}).get('status')=='ok' else 'neověřeno / chyba vyhledávání')), 
                   'cards':len([i for i in output['catalog'] if i['shop']==shop]),
                   'reason':'Sběr přes vyhledávání celého sortimentu; pokrytí není garantováno',
                   **coverage['by_store'][shop]}
             for shop in cfg.get('sources',{})}
    snapshot={'date':now.date().isoformat(),'checked_at':now.isoformat(timespec='minutes'),
       'sources':sources,'source_urls':{'Rohlík':'https://www.rohlik.cz/','Košík':'https://www.kosik.cz/'},'delivery':cfg.get('delivery',{}),
       'postcode_specific_prices_verified':False,
       'catalog':output['catalog'], 'offers':offer_dicts,'catalog_coverage':coverage,
       'product_details':enrich,
       'changes':lib.compare_changes(output['offers'],previous),
       'demo':demo,'disclaimer':'Veřejné vyhledávání napříč katalogem: nereprezentuje úplné pokrytí celého sortimentu ani lokální dostupnost PSČ 149 00.'}
    lib.write_snapshot(snapshot)
    print(f"{now.isoformat(timespec='minutes')} | katalog {len(output['catalog'])} | slevy {len(output['offers'])} | dotazy {coverage['queries_responded_24h']}/{coverage['queries_planned']}")
    return 0 if demo or coverage['batch_errors'] < coverage['batch_queries'] or any(x.get('status')=='ok' for x in fallback.values()) else 2
