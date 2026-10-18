**Verze v6 – připravené přímé nasazení GitHub Pages přes GitHub Actions. Web dosud není nasazen.**

Podrobný a aktuální postup: `NASAZENI_ONLINE.md`.

# Rohlík × Košík – katalog v6 pro ChatGPT Free / iPhone

Aktualizace: 18. 10. 2026. Vytvořen kompletní seznam podle poslední zprávy uživatele.

## Nejsnazší spuštění na jiném účtu

**Na cílový iPhone přenést jen soubor `TRANSFER_CHATGPT_FREE_IPHONE_V5.txt`.** Jeho celý text vložit do běžného chatu ChatGPT na účtu Free. V chatu se musí objevit skutečná karta/confirmace vytvoření denní naplánované úlohy. Pak v iOS a ChatGPT povolit oznámení. Nic se neinstaluje, není nutný Python.

Jedna úloha denně **ráno v flexibilním okně**, časové pásmo Europe/Prague. Free účet může mít maximálně 3 aktivní naplánované úlohy; konkrétní podporu vždy ověřit v účtu/app. Aktuální oficiální dokumentace: https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt .

## Konfigurace

- **72 výběrových pravidel + 2 konkrétní oblíbené výrobky**, 26 původních P1, 46 původních P2 (plus 2 nové konkrétní oblíbené produkty P1).
- P1 **5 %**, P2 **15 %**, filtrace podle značek i podkategorií; konkrétní varianty mají přednost.
- Bez konkrétních URL neprobíhá garance identické varianty; doporučujeme doplnit konkrétní výrobky postupně.
- Zewa: Deluxe Standard papírové kapesníky 3vrstvé 10×10 ks (P1). Syoss: MEN Intense Power šampon 440 ml (P1), spárovaný Rohlík ↔ Košík. U Syoss rozhoduje typ, nikoli barva obalu.
- Vstupní „Arial“ bylo vyloženo jako **Ariel**, „Chodur“ jako **Chodura** a „Želetava Smetanino“ jako **Želetava Smetanito**. „Hera/Omega/Rama/Flora“ jsou v kategorii rostlinných tuků, ne klasického másla.
- Kategorie ryby má zatím **žádné konkrétní sledované druhy** (nezadány).
- Doručovací oblast: **PSČ 149 00**. U každé kontroly se musí ověřit, zda web tuto lokalitu opravdu zohlednil. Python sběrač zatím získává veřejné ceny bez doložené lokalizace; ty nelze označit za ceny garantované pro PSČ 149 00.

## Vlastní webový dashboard – jen samostatně

Složka obsahuje **rozšířený prototyp Python + Playwright + GitHub Pages**: `monitor.py`, `config.json`, `docs/index.html`, `.github/workflows/prices.yml`, `tests/`.

Pozor: žádná veřejná URL dashboardu zatím nevznikla. Aby existovala a pravidelně se aktualizovala, musí se projekt nasadit na externí hosting a ověřit reálné získávání cen. To **nelze** provést pouhým vložením textu do ChatGPT Free na iPhonu. Python sběrač pracuje se vzorkem veřejných slevových karet, **nikoli s kompletními produktovými katalogy**; srovnání cen páru vyžaduje, aby se obě nabídky objevily ve stejném sběru. Úplnost/správnost reálného sběru obou e-shopů zatím není ověřena. Žádná dnešní cena se neprezentuje jako ověřená.

Případný GitHub hosting lze nasadit z kořene balíčku; viz předchozí podrobná přiložený `NASAZENI_ONLINE.md`. Kód je přiložen jen pro budoucí rozšíření; pro přenos na cílový účet **postačuje TXT**.

## Testování

Ověřeno 14 jednotkovými testy, které nepředstavují ostrý test sběru cen z webů.


`python -m unittest discover -s tests -v` ověřuje pravidla filtrování, výjimky (Zero/Light, ochucené vody, omáčky), řazení priorit, ceny a bezpečné srovnávání totožných výrobků. Demo uvádí syntetické ceny a je oddělené od provozních výsledků.

## Základní sledovací seznam

• Maso: ★ Drůbeží prsní řízky; ★ Drůbeží stehna; ★ Vepřová krkovice; ★ Vepřová panenka; ★ Hovězí svíčková (maso)
• Uzeniny / šunky: Šunky – LE & CO; Šunky – Chodura; Šunky – Wein; Šunky – Kostelecké uzeniny
• Uzeniny / salámy: Salámy – Kmotr; Salámy – Chodura; Salámy – Ponnath; Salámy – Krahulík
• Uzeniny / párky a klobásy: Párky a klobásy – Ponnath; Párky a klobásy – Chodura; Párky a klobásy – Kostelecké uzeniny
• Sýry / plátkové: Plátkové sýry – MADETA; Plátkové sýry – Leerdammer; Plátkové sýry – Président
• Sýry / tavené: ★ Želetava Smetanito; Veselá kráva; ★ Madeta Lipno
• Sýry / plísňové: Plísňové sýry – Král Sýrů; Plísňové sýry – Sedlčanský; Plísňové sýry – Président
• Sýry / mozzarella a salátové: Galbani – mozzarella / salátový sýr
• Majonézy: Hellmann’s – majonézy
• Másla a tuky: ★ Madeta máslo; Hera – tuky na pečení / roztírání; Omega – tuky na pečení / roztírání; Rama – tuky na pečení / roztírání; Flora – tuky na pečení / roztírání
• Nápoje / vody: Aquila – neperlivá, jemně perlivá, kojenecká; Rajec – neperlivá, jemně perlivá, kojenecká; Dobrá voda – neperlivá, jemně perlivá, kojenecká
• Nápoje / limonády: ★ Coca-Cola Original (bez Zero/Light)
• Ovoce: ★ Avokádo; ★ Banány; ★ Borůvky; ★ Maliny; ★ Citrony; ★ Hroznové víno
• Zelenina: ★ Okurky; ★ Rajčata; ★ Cherry rajčata; ★ Mrkev; ★ Papriky
• Sladké: ★ Studentská pečeť – mléčná/hořká/hořko-mléčná; ★ Miňonky – hořké; ★ Fidorky – kokosové; ★ Kokosky
• Těstoviny a rýže: Panzani – těstoviny a rýže
• Papír a hygiena: ★ Zewa Deluxe Standard kapesníky 3vrstvé 10 × 10 ks; Zewa – ostatní kapesníky / ubrousky / toaletní papír; ★ Linteo – vlhčené ubrousky
• Kosmetika: AXE – sprchové gely, šampony, deodoranty; ★ Syoss Men Intense Power šampon 440 ml
• Dentální hygiena: Signal – zubní pasty; Colgate – zubní pasty; Parodontax – zubní pasty
• Holení: Wilkinson – jednorázové žiletky
• Praní: Ariel – prací prostředky; Persil – prací prostředky; Lenor – aviváže; Silan – aviváže; Vanish – odstraňovače skvrn
• Úklid: Bref – čisticí prostředky; WC Net – čisticí prostředky; Domestos – čisticí prostředky; Savo – čisticí prostředky; Cif – čisticí prostředky; Clin – čisticí prostředky; ★ Jar – citron
