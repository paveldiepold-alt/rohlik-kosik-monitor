# Rohlík × Košík – v14: papírová hygiena a kuchyňské utěrky

## Co sledovat
- **Zewa kapesníky v balíčcích:** pouze řada **Deluxe**, především **Standard / Original**. Žádné kapesníky v krabici se nesmějí podstrčit za balíčkové.
- **Papírové kuchyňské utěrky:** **jakákoliv značka**, pouze papírové, ne textilní/vlhčené ani dezinfekční ubrousky.
- **Papírové kapesníky v krabici:** **jakákoliv značka**, ale musí být **3vrstvé** a z názvu musí být jasné balení v boxu/krabici.
- **Zewa toaletní papír a papírové ubrousky:** zachovány z původního seznamu.
- **Linteo vlhčené ubrousky:** beze změny.

## Tři konkrétní odkazy (zkrácené na kanonické URL)
- https://www.kosik.cz/p82407-zewa-deluxe-standard-kapesniky-3-vrstve
- https://www.kosik.cz/p82477-zewa-deluxe-family-kapesniky-3vrstve
- https://www.kosik.cz/p233874-zewa-wisch-weg-original-kuchynske-uterky-4-role

## Limity
Toto je oprava sledovací logiky, nikoli potvrzení dnešních cen. Monitor prohledává veřejné akční stránky, ne kompletní katalog, takže některé relevantní akce se na dashboardu nemusí objevit. U krabičkových kapesníků vyžadujeme 3 vrstvy a důkaz, že jde o box; výjimkou je výrobek Zewa Deluxe Family 90 ks, u něhož je provedení v krabici ověřeno. Produktové fotografie to nemění.

## Nasazení BEZ GitHub propojení v ChatGPT
V hlavním GitHub repozitáři vyměnit kód souborů `config.json`, `monitor.py`, `tests/test_v12_preferences_and_images.py` a navíc vytvořit `tests/test_paper_goods_v14.py`. Pomocné testy patří na GitHub, protože GitHub Actions spouští všechny testy před publikováním. **Neměnit `docs/index.html`**; aktuální responzivní vzhled v13 funguje automaticky i pro nové kategorie.

Druhá možnost: nahraj rozbalené soubory ze ZIPu se zachováním cest do repozitáře; ZIP samotný nikdy nenahrávej.

Po commitu otevři GitHub Actions -> `Rohlík Košík – scan and publish`. Vynucený běh přes `Run workflow` může aktualizovat dashboard rychleji. Po zelené fajfce obnov stránku.

**Ověření konkrétní varianty:** Zewa Deluxe Family z Košíku je 3vrstvý BOX 90 ks; proto patří do kategorie krabičkových kapesníků, nikoli do malých balíčků. Vlastnost potvrzují produktové nabídky pro EAN 4006670128002.
