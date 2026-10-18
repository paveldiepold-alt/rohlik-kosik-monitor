# Rohlík × Košík — v17, oprava podle skutečných diagnostických dat

Datum diagnostiky: 18. října 2026, 18:33 (Europe/Prague)
Vstupy: `search_status.json` a `latest.json` nahrané uživatelem.

## Co je PŘÍMO prokázáno

- Vyhledávací plán měl 196 dotazů (98 pro každý obchod). Během posledních 24 h bylo 72 dotazů zkusmo zpracováno, z toho jen 6 poskytlo výsledky; 66 dotazů mělo chybu.
- Košík: **0/36 úspěšných vyhledávání**, všechny dosavadní pokusy hlásily `search_unavailable` / „Nenalezeno veřejné vyhledávací pole“.
- Rohlík: **6/36 úspěšných**, sedmý dotaz dostal `HTTP 429`, poté dalších 29 dotazů nebylo vyhledáno (`skipped_rate_limit`).
- V `latest.json` bylo **52 produktů: 44 Rohlík + 8 Košík**. Z toho **40 výrobků nemělo ověřenou prodejní cenu** (`price:null`).
- Z 41 položek v kategorii maso bylo **9 produktů Applaws pro kočky**, dále 2 kuřecí prsa s kostí a 1 dětská kapsička se zeleninovým pyré.
- Zaznamenáno **11 zlevněných položek**, z nich 8 z Košíku přes záložní akční stránku.
- Report enrichment: `visited=3`, `filled=3`, `photos_cached=3` (pouze Rohlík). Původní kód volal obohacení detailů **před** přidáním Košíkových nabídek z fallback stránky. Proto fotografie a specifikace těchto 8 výrobků nebyly vůbec předmětem pokusu o načtení detailu.
- PSČ 149 00 je preference; ceny nejsou ověřeny pro toto doručovací místo.

## Opraveno v kódu

1. Zpřísněna kategorizace syrového masa: odfiltrována krmiva a kapsičky a pro kuřecí prsní řízky vyloučeny varianty *s kostí*. Archivní katalogový cache při každém spuštění znovu ověřuje pravidla.
2. Obohacení produktových detailů a fotek probíhá až po načtení záložních akčních nabídek **obou obchodů**, takže Košík bude mít šanci získat obrázky, pokud jsou detaily veřejně dostupné.
3. Vyhledávací pole: přidána čekací okna na pozdní vykreslení, širší sadu veřejných selektorů a bezpečnou diagnostiku metadat vyhledávacích prvků (bez soukromých hodnot a cookies). To **nezaručuje** odstranění problémů Košíku; pokud search box dál nebude přístupný, v diagnostice zjistíme bližší důvod.
4. Po druhém selhání nalezení vyhledávacího pole se v daném běhu další dotazy téhož obchodu přeskočí a označí `skipped_search_unavailable`, aby 36 chyb nevypadalo jako 36 nezávislých překážek.
5. Snížen počet vyhledávání na **8 na jeden běh** (pro 2 obchody max. 4 na obchod) kvůli HTTP 429. Je to konzervativní opatření, nikoli záruka odblokování.
6. Ukládání pozorovaných produktů prodlouženo na 10 dní, ale produkty pro aktuální srovnání a ceny se i nadále zobrazují **pouze pokud jsou čerstvě ověřené (18 hodin)**. Přidáno vyhodnocení pokrytí za 10 dní a samostatně za 24 hodin.
7. Nezjištěná cena je explicitně označena `cena nezjištěna`.

## Co NEBYLO ověřeno

- Živý automatický přístup na oba e-shopy z GitHub Actions, zejména Košík.
- Aktuální úplnost katalogu; 8 dotazů na běh / 3 běhy denně znamená přibližně 8–9 dní pro 196 dotazů i bez blokace.
- Faktické stažení fotografií z Košíku po přesunu enrichment fáze.
- Ověřené individuální ceny a dostupnost pro PSČ 149 00.

## Přesný postup nasazení (bez Reconnect / GitHub pluginu)

1. Stáhni `Rohlik_Kosik_v17_DIAGNOSTIKA_OPRAVA.zip`.
2. Rozbal ZIP. **Obsah ZIPu nemá nadřazenou složku**; jsou v něm `catalog_scan.py`, `monitor.py`, `config.json`, `docs/index.html`, upravený test a nový test.
3. Na GitHubu v repozitáři `paveldiepold-alt/rohlik-kosik-monitor` použij na stránce Code `Add file → Upload files`. Nahraj **obsah rozbalené složky**, ne samotný ZIP. Zachovej cesty `docs/index.html` a `tests/...`; ostatní hlavní soubory přímo do rootu. Potvrď změny.
4. Zkontroluj v Actions workflow `Rohlík Košík – scan and publish` a vyčkej na dokončení.
5. Z dashboardu otevři `data/search_status.json`, především záznamy `Košík::...` s metadaty `title/inputs/buttons`. Pokud stále naskakuje `search_unavailable`, pošli nový JSON pro cílenou opravu konkrétního UI. Nesnaž se opakovaným spouštěním přebít rate limit Rohlíku.
6. `docs/data` **nemaž ani nepřepisuj**: obsahuje reálnou historii a obrázky. Balíček v17 jej vůbec neobsahuje.

Poznámka: soubor `monitor.py` stále obsahuje původní základ projektu v16; v17 se jedná pouze o cílené změny podle skutečných diagnostických souborů.
