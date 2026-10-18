# Rohlík × Košík Price Monitor v6 – ONLINE nasazení

## Aktuální stav
Hotový projekt pro publikaci. **NENÍ ještě online:** veřejná adresa vyžaduje propojení s GitHub účtem a vytvoření repozitáře. Nepublikuj demo výsledky jako reálné. Nevyžadujeme přihlašovací heslo do Rohlíku/Košíku.

## Proč předchozí v5 nezobrazovala aktualizace
Předchozí workflow po kontrole cen pouze měnilo `docs/` a vytvářelo commit pomocí `GITHUB_TOKEN`. GitHub Pages při nasazení z větve nepovažuje takové commity za událost vyvolávající nové sestavení. v6 nyní používá v JEDINÉM workflow kroky `configure-pages@v5` → `upload-pages-artifact@v3` → `deploy-pages@v4`. Toto je dokumentovaný způsob nasazení přímo přes GitHub Actions.

## Nejjednodušší cesta – propojení GitHubu s ChatGPT
1. Na tomto účtu ChatGPT v nabídce Plugins/APPS připoj GitHub a povol přístup k repozitáři pro price monitor. Není nutné připojovat GitHub k cílovému iPhonu.
2. Napiš zde „GitHub připojen“ a zopakuj požadavek nasazení. Pokud zde budou dostupné akce vytváření repozitáře/souborů, lze provést nahrání v tomto chatu.
3. Po skutečném nasazení získáš veřejnou URL například `https://<uzivatel>.github.io/rohlik-kosik-monitor/`; **konkrétní URL nelze předem tvrdit jako aktivní**.
4. Na cílovém ChatGPT Free účtu iPhone se vloží až finální přenosový prompt včetně ověřené URL reportu.

## Alternativa – ručně GitHub na počítači
1. Rozbal ZIP. Na GitHub.com vytvoř nový **veřejný** repozitář `rohlik-kosik-monitor` a nahraj obsah SLOŽKY `rohlik_kosik_monitor_v6`, nikoliv samotnou nadřazenou složku. Zachovej i skrytou složku `.github/workflows/`.
2. Ve `Settings → Pages → Build and deployment → Source` nastav **GitHub Actions** (nikoli Deploy from a branch).
3. V `Actions → Rohlík Košík – scan and publish → Run workflow` jednou ručně spusť; automatika běží 3× denně.
4. V `Actions` otevři poslední běh a přečti chyby, pokud jsou. Ve `Settings → Pages` si otevři uvedenou URL, až bude skutečně aktivní.
5. Ověř `report.html` a `data/latest.json`; pokud stránky u obou obchodů blokují sběr, zobrazí se stav `CHYBA` nebo `Nenalezeny produktové karty`, NIKOLI vymyšlená cena.

GitHub Free: GitHub Pages je dostupný pro veřejný repozitář. Stránka je veřejná; nezveřejňuj osobní data. Údaje o PSČ 149 00 a seznam preferencí budou veřejně čitelné. Nevkládej cookies, hesla ani tokeny.

## Přenos na druhý ChatGPT Free účet
Až online adresa skutečně funguje, vlož do pole `DASHBOARD_URL` a `REPORT_URL` v `TRANSFER_CHATGPT_FREE_IPHONE_V6.txt` ověřené adresy z GitHub Pages. Na cílovém iPhonu tento jediný text vlož do ChatGPT Free a aktivuj DENNÍ úlohu (pokud ji účet podporuje). Pokud úloha vznikla, zobrazí se systémové potvrzení. ChatGPT Free zůstává oddělený od GitHubu.

## Co nelze garantovat
- Cena pro PSČ 149 00 není potvrzena pouhým zadáním PSČ do konfigurace.
- Obě stránky mohou omezovat automatizované návštěvy.
- Stránky akčních nabídek neobsahují celý sortiment ani všechny slevy značek.
- Pro ověřená srovnání musí být dostupné oba shodné výrobky ve stejném aktuálním sběru.
- Aktuální proces sběru 3× denně běží nezávisle na jedné naplánované úloze ChatGPT.
