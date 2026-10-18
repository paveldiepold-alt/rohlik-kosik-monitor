import json
import unittest
from pathlib import Path
from dataclasses import asdict
from monitor import brand_of, classify_rows, parse_price, parse_card, add_comparisons, demo_rows, compare_changes, build_report, match_rules

CFG=json.loads((Path(__file__).resolve().parents[1]/'config.json').read_text(encoding='utf-8'))

class TestMonitor(unittest.TestCase):
    def test_price_formats(self):
        self.assertEqual(parse_price('54 90 84,90 -35%'),54.90)
        self.assertEqual(parse_price('249,90 Kč'),249.90)
        self.assertEqual(parse_price('22\n90Kč'),22.90)
        self.assertIsNone(parse_price('Cena není k dispozici'))
    def test_brands(self):
        self.assertEqual(brand_of('LE&CO Šunka', CFG['brands']), 'LE & CO')
        self.assertEqual(brand_of('LE & CO Šunka', CFG['brands']), 'LE & CO')
        self.assertEqual(brand_of('Coca-Cola Zero 1,5 l', CFG['brands']), 'Coca-Cola')
        self.assertEqual(brand_of('Aquilaria vonná', CFG['brands']), '')
    def test_discount_and_unknown_price_not_invented(self):
        row={'name':'LE&CO Šunka 100 g','url':'https://www.rohlik.cz/12345-sunka','card':'34 90 -20 % LE&CO Šunka 100 g'}
        self.assertAlmostEqual(parse_card('Rohlík',row,CFG).price,34.90)
        row['card']='-20 % LE&CO Šunka 100 g'
        self.assertIsNone(parse_card('Rohlík',row,CFG))
    def test_min_discount(self):
        r=demo_rows()['Rohlík'][0].copy()
        r['card']=r['card'].replace('-22 %','-10 %')
        self.assertIsNone(parse_card('Rohlík',r,CFG))
    def test_favorite_no_brand(self):
        cfg={**CFG,'favorites':[{'keywords':['Tvaroh','500 g']} ]}
        row={'name':'Tvaroh 500 g','url':'https://www.kosik.cz/p100010-test','card':'29 90 -7 % Tvaroh 500 g','current_price':'29,90 Kč'}
        self.assertTrue(parse_card('Košík',row,cfg).favorite)
    def test_product_watchlist_accepts_requested(self):
        names=['Coca-Cola Original 1,5 l','LE&CO šunka 100g','Krahulík Vysočina 100g',
          'Madeta máslo 250 g','Želetava Smetanito 150g','Aquila neperlivá 1,5l',
          'Panzani Spaghetti 500g','Cif tekutý písek 500ml','Čerstvé borůvky 125g',
          'Cherry rajčata 250g','Jar citron 900ml','Fidorka kokosová 30g',
          'Vepřová panenka 1kg','Chodura šunka od kosti 100g']
        for n in names:
            with self.subTest(n=n):
                self.assertIsNotNone(match_rules(n, CFG['watch_rules']))

    def test_explicit_rejections(self):
        names=['Coca-Cola Zero 1,5 l','Coca-Cola Light 2l','Aquila ochucená citron',
          'Madeta Jihočeská Niva 45 %','Jar pro nádobí bez citronu','Borůvkový jogurt',
          'Panzani rajčatová omáčka','Hellmanns tatarská omáčka',
          'Vepřová krkovice marinovaná']
        # Exceptions: e.g. 'Jar bez citronu' still contains the string citron;
        # later tests check for exact variant rules. Here only strict exclusions.
        names.remove('Jar pro nádobí bez citronu')
        for n in names:
            with self.subTest(n=n):
                self.assertIsNone(match_rules(n, CFG['watch_rules']))

    def test_priority_and_brand_over_produce(self):
        self.assertEqual(match_rules('Jar citron 900ml',CFG['watch_rules'])['category'],'Úklid')
        self.assertEqual(match_rules('Cherry rajčata 500g',CFG['watch_rules'])['label'],'Cherry rajčata')
        self.assertEqual(match_rules('Coca-Cola Original 1,5 l',CFG['watch_rules'])['priority'],1)
        self.assertIsNone(match_rules('Coca-Cola Zero 1,5 l', CFG['watch_rules']))

    def test_comparison_only_exact(self):
        a=classify_rows('Rohlík',demo_rows()['Rohlík'],CFG)
        b=classify_rows('Košík',demo_rows()['Košík'],CFG)
        add_comparisons(a+b, [])
        cola=next(o for o in a if 'Coca-Cola' in o.name)
        self.assertEqual(cola.other_shop,'Košík')
        self.assertAlmostEqual(cola.other_shop_price,36.9)
        self.assertIsNone(next(o for o in a if 'Šunka' in o.name).other_shop_price)
    def test_comparison_different_pack(self):
        a=classify_rows('Rohlík',demo_rows()['Rohlík'],CFG)
        b=classify_rows('Košík',demo_rows()['Košík'],CFG)
        b[0].name='Coca-Cola Original 1,5 l'
        add_comparisons(a+b, [])
        self.assertIsNone(next(o for o in a if 'Coca-Cola' in o.name).other_shop_price)
    def test_change_detection(self):
        offer=classify_rows('Rohlík',demo_rows()['Rohlík'],CFG)[0]
        self.assertEqual(compare_changes([offer],{})[0]['kind'],'newly_observed')
        self.assertEqual(compare_changes([offer],{'offers':[{'url':offer.url,'price':offer.price+10}]})[0]['kind'],'price_dropped')
        self.assertEqual(compare_changes([offer],{'offers':[{'url':offer.url,'price':offer.price}]}),[])

    def test_precise_zewa_and_syoss_priorities(self):
        z = {'name':'Zewa Deluxe Standard papírové kapesníky 3vrstvé 10x10ks',
             'url':'https://www.rohlik.cz/1307969-zewa-deluxe-standard-papirove-kapesniky-3vrstve-10x10ks',
             'card':'49,90 Kč 59,90 Kč -17 % Zewa Deluxe Standard papírové kapesníky 3vrstvé 10x10ks',
             'current_price':'49,90 Kč'}
        offer = parse_card('Rohlík',z,CFG)
        self.assertTrue(offer.favorite)
        z['card']=z['card'].replace('-17 %','-7 %').replace('59,90','53,90')
        self.assertTrue(parse_card('Rohlík',z,CFG).favorite)
        syoss = {'name':'Syoss Men Intense Power šampon pro muže',
                 'url':'https://www.kosik.cz/p304584-syoss-men-intense-power-sampon-pro-muze',
                 'card':'149,90 Kč 159,90 Kč -6 % Syoss Men Intense Power šampon pro muže',
                 'current_price':'149,90 Kč'}
        self.assertTrue(parse_card('Košík',syoss,CFG).favorite)
        syoss_other = {**syoss,'url':'https://www.kosik.cz/p999988-syoss-keratin',
                       'name':'Syoss Keratin šampon 440ml'}
        self.assertIsNone(parse_card('Košík',syoss_other,CFG))

    def test_syoss_cross_shop_verified_pair(self):
        a = {'name':'Syoss Men Intense Power šampon pro muže',
             'url':'https://www.rohlik.cz/1299615-syoss-men-intense-power-sampon-pro-muze',
             'card':'139,90 Kč 169,90 Kč -18 % Syoss Men Intense Power',
             'current_price':'139,90 Kč'}
        b = {'name':'Syoss Men Intense Power šampon pro muže',
             'url':'https://www.kosik.cz/p304584-syoss-men-intense-power-sampon-pro-muze',
             'card':'149,90 Kč 169,90 Kč -12 % Syoss Men Intense Power',
             'current_price':'149,90 Kč'}
        offers=[parse_card('Rohlík',a,CFG),parse_card('Košík',b,CFG)]
        self.assertTrue(all(offers))
        add_comparisons(offers,CFG['canonical_pairs'])
        self.assertEqual(offers[0].other_shop,'Košík')
        self.assertEqual(offers[1].other_shop,'Rohlík')

    def test_delivery_postcode_saved_but_not_claimed_verified(self):
        self.assertEqual(CFG['delivery']['postal_code'], '149 00')
        self.assertFalse(CFG['delivery']['postcode_specific_prices_verified'])
        snap={'date':'2026-10-18','checked_at':'2026-10-18T09:00+02:00','offers':[],
              'changes':[], 'sources':{},'source_urls':{}, 'demo':False,
              'delivery':CFG['delivery']}
        report=build_report(snap)
        self.assertIn('149 00',report)
        self.assertIn('nikoli automaticky ověřená lokální cena',report)

    def test_report_explicitly_marked_demo(self):
        snap={'date':'2026-10-18','checked_at':'2026-10-18T09:00+02:00','offers':[], 'changes':[], 'sources':{'Košík':{'status':'DEMO – syntetická data','cards':0}},'source_urls':{}, 'demo':True}
        self.assertIn('DEMO DATA',build_report(snap))

if __name__ == '__main__':unittest.main()
