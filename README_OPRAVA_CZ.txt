ROHLÍK × KOŠÍK MONITOR v15 — ZPŘESNĚNÍ SBĚRU A NOVÝ SEZNAM MASA

ZÁVĚR AUDITU
Osm položek NEZNAMENÁ, že na obou obchodech existuje pouze osm akcí.
Dosavadní monitor čte jen dvě hlavní stránky akcí, na každé z nich provedl
pouze devět posunů a končil nejvýše na 700 načtených kartách. Navíc každá
karta musí projít rozpoznáním ceny, slevy a podmínkami výběru. Zbytek
sortimentu proto monitor vůbec nemusel vidět. Dashboard nesmí označovat
výsledek jako kompletní seznam všech zlevněných výrobků.

V15 OPRAVUJE
1. Prochází delší část akčních stránek (až 85 kroků) a zkouší tlačítko
   „Načíst další“. Limit sběru navýšen na 3500 karet na obchod.
2. Do JSON reportu zapisuje informaci o částečném/nejistém pokrytí.
   Dashboard výrazně upozorní, že jde o NEÚPLNÝ VZOREK.
3. MASO: pouze syrové kuřecí prsní řízky/prsa, kuřecí stehna,
   vepřová krkovice, vepřová panenka a hovězí svíčková.
   Krůtí maso už se nesleduje. Uplatňuje se zákaz konzerv, marinád,
   uzeného, sušeného, hotových jídel a masových pochutin.
4. Rozpozná i názvy typu „Campese Kuřecí vykostěná stehna...“.
5. Kontroluje zobrazenou dvojici aktuální/původní ceny proti procentu slevy,
   aby například u hroznů neukazoval původní cenu 111,92 Kč místo
   akční ceny 55,92 Kč, pokud jsou na kartě přítomny obě částky.
6. Ponechává historii, dashboard na iPhonu i ostatních 75 pravidel.

DŮLEŽITÉ OMEZENÍ
Ani v15 ještě neprohledává celý katalog Rohlíku a Košíku ani každou
samostatnou kategorii či značku. Limit 3500 a delší scroll zvětšují
vhodný vzorek; NEZARUČUJÍ úplnost. Přesné ceny a sklad pro PSČ 149 00
nejsou bez volby adresy v e-shopu ověřené. Rozsah nabídek přístupných
bez přihlášení se může odlišovat.

TESTY
Lokálně úspěšně prošlo 54 automatických unit testů na logiku parseru,
klasifikaci, ceny a související funkce. Živý kompletní sběr na GitHubu
zatím nebyl vyzkoušen a jeho účinnost není zaručena.

INSTALACE — PŘESNĚ 4 EXISTUJÍCÍ SOUBORY, +1 VOLITELNÝ TEST
1. monitor.py -> /monitor.py
2. config.json -> /config.json
3. docs/index.html -> /docs/index.html
4. tests/test_raw_meat_and_labels.py -> /tests/test_raw_meat_and_labels.py
5. Volitelně přidej nový tests/test_coverage_and_meat_v15.py.

Nezapomeň aktualizovat test z kroku 4. Starší test stále vyžaduje
krůtí maso a po správné změně katalogu by GitHub Actions skončily chybou.

Repozitář: https://github.com/paveldiepold-alt/rohlik-kosik-monitor
Actions: https://github.com/paveldiepold-alt/rohlik-kosik-monitor/actions
Dashboard: https://paveldiepold-alt.github.io/rohlik-kosik-monitor/

Obě hlavní akční stránky: https://www.rohlik.cz/cenove-trhaky
https://www.kosik.cz/s1-akce

Žádné připojování GitHubu v ChatGPT není potřeba, soubory nahraď ručně v GitHubu.
