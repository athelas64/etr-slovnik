# Ako prispieť do slovníka

Ďakujeme. Slovník je len taký dobrý, aké sú vysvetlenia v ňom, a najlepšie vysvetlenia
píšu ľudia, ktorí s čitateľmi pracujú.

## Najjednoduchšia cesta: formulár „Navrhnúť slovo“

1. Otvorte [Issues → New issue → Navrhnúť slovo](../../issues/new/choose).
2. Vyplňte slovo, vysvetlenie a odkiaľ vysvetlenie pochádza.
3. Správca ho prepíše do súboru, skontroluje a zlúči. Vaše meno alebo organizácia ostane
   v poli `contributor`.

## Pull request

1. Upravte `slovniky/verejna-sprava-sk.json` (vrstva verejnej správy) alebo
   `slovniky/hurraki-sk.json` (adaptácia Hurraki).
2. Spustite kontrolu:

   ```
   pip install jsonschema
   python scripts/validate.py
   ```

3. Pri zmene hesla zvýšte `version` súboru (tvar `RRRR-MM-DD` alebo `RRRR-MM-DD.N`) a
   `updated`. `manifest.json` neupravujte, prepíše sa po zlúčení.
4. Otvorte pull request. Popíšte, odkiaľ vysvetlenie je a kto ho overil.

## Pravidlá pre vysvetlenie (`easy`)

Platia [európske pravidlá ľahko čitateľného textu](https://www.inclusion.eu/european-standards-how-to-use-easy-to-read)
(Inclusion Europe, „Informácie pre všetkých“):

- Prvá veta povie, čo slovo znamená: „Podnet je správa o tom, že niekto porušil práva.“
- Jedna myšlienka v jednej vete. Najviac 15 slov. Každá veta na novom riadku (`\n`).
- Slová, ktoré ľudia poznajú. Príklad zo života do poľa `example`.
- Bez zátvoriek, lomiek, pomlčiek, bodkočiarok, paragrafov a percent. Bez skratiek;
  ak skratku čitateľ stretne, vysvetlite ju vetou („CRPD je skratka pre tento dohovor.“).
- Čísla číslicami, dátumy slovami, bez rímskych číslic.
- Oslovenie „vy“, úrad je „úrad“ alebo „my“ podľa kontextu. Dospelý tón.
- „Ľudia so zdravotným postihnutím“, „ľudia s mentálnym znevýhodnením“. Nikdy „postihnutí“.
- Čítač obrazovky, nie „čítačka“.
- Nevymýšľajte fakty: poplatky, lehoty a sumy patria do textu úradu, nie do slovníka.

## Čo sa kontroluje automaticky

`scripts/validate.py` na každom pull requeste: JSON Schema, jedinečné `id`, dĺžka viet,
jedna veta na riadok, zakázané znaky, a že strojovo preložené heslo nie je označené ako
`reviewed` alebo `reader-checked`.

## Stavy hesla

| `status` | Kto ho smie nastaviť |
|---|---|
| `draft` | ktokoľvek |
| `reviewed` | odborník na ľahko čitateľný text, ktorý heslo prečítal a upravil |
| `reader-checked` | po overení skupinou čitateľov s mentálnym znevýhodnením; do poľa `note` napíšte kedy a s kým |

## Licencia príspevkov

Príspevkom do `slovniky/verejna-sprava-sk.json` súhlasíte s jeho zverejnením pod
licenciou súboru (teraz CC BY 4.0; po rozhodnutí MIRRI sa môže zmeniť, o čom budú
prispievatelia informovaní). Príspevky do `slovniky/hurraki-sk.json` sú CC BY-SA 3.0.
