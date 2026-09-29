# etr-slovnik – slovník ťažkých slov pre ľahko čitateľné texty

Spoločný, otvorený slovník ťažkých slov a ich vysvetlení v ľahko čitateľnom jazyku
(easy-to-read) pre orgány verejnej správy na Slovensku. **Overovací prototyp** (proof of
concept): repozitár je zatiaľ súkromný, licencia a správa sú predbežné do rozhodnutia
MIRRI.

Prečo: ľahko čitateľný text musí každé ťažké slovo vysvetliť. Keď každý úrad vysvetľuje
„podnet“, „spôsobilosť na právne úkony“ alebo „osobné údaje“ inak, čitateľ s mentálnym
znevýhodnením sa musí učiť nanovo pri každom liste. Jeden zdieľaný slovník znamená jedno
vysvetlenie, ktoré čitateľ stretne všade a ktoré overili ľudia, pre ktorých je určené.

## Čo je v repozitári

| Cesta | Obsah |
|---|---|
| `slovniky/verejna-sprava-sk.json` | Slovník verejnej správy (vrstva `public`), CC BY 4.0. Základ: vysvetlenia z webu Úradu komisára pre osoby so zdravotným postihnutím, upravené tak, aby platili pre každý úrad. |
| `slovniky/hurraki-sk.json` | Slovenská adaptácia lexikónu [Hurraki](https://hurraki.de) (vrstva `global`), CC BY-SA 3.0. Prvé heslá sú strojový preklad označený `origin: machine-translated`, kým ich neskontroluje človek. |
| `schema/slovnik.schema.json` | JSON Schema pre všetky súbory slovníka. |
| `manifest.json` | Zoznam súborov s odtlačkom sha256; nástroj si z neho zistí, či má nové heslá. |
| `scripts/validate.py` | Kontrola schémy a pravidiel ľahko čitateľného textu (max. 15 slov vo vete, jedna veta na riadok, bez zátvoriek a lomiek). Beží pri každom pull requeste. |
| `scripts/build_manifest.py` | Prepíše `manifest.json`. Beží po každom zlúčení do `main`. |
| `scripts/harvest_komisar.py` | Stiahne dvojice štandardný text / ľahko čitateľný text z komisar.sk do `zdroje/komisar-pary.json`. |
| `scripts/harvest_hurraki.py` | Stiahne Hurraki cez MediaWiki API (nemecké a anglické vydanie) do JSON Lines, s číslami revízií pre neskoršiu aktualizáciu. |
| `zdroje/` | Surové podklady, z ktorých heslá vznikli (kvôli dohľadateľnosti). |

## Tvar hesla

```json
{
  "id": "podnet",
  "term": "podnet",
  "forms": ["podnety", "podať podnet", "podanie podnetu"],
  "easy": "Podnet je správa o tom, že niekto porušil práva.\nPodnet môže podať každý.\nZa podanie podnetu nič neplatíte.",
  "example": "Napríklad napíšete, že vás úrad nepustil dnu na vozíku.",
  "domain": "úrad",
  "source": {"name": "Úrad komisára pre osoby so zdravotným postihnutím", "url": "https://www.komisar.sk/pre-verejnost", "fetched": "2026-09-29"},
  "status": "draft",
  "origin": "adapted",
  "added": "2026-09-29",
  "contributor": "athelas64"
}
```

- `easy` je vysvetlenie pre čitateľa: jedna veta na riadok, najviac 15 slov vo vete,
  bez zátvoriek, lomiek, pomlčiek, bodkočiarok a skratiek, oslovenie „vy“.
- `forms` sú tvary, podľa ktorých nástroj slovo v texte nájde (množné číslo, pády, skratky).
- `status`: `draft` navrhnuté, `reviewed` skontroloval odborník na ľahko čitateľný text,
  `reader-checked` overili čitatelia s mentálnym znevýhodnením. Len `reader-checked`
  heslo smie niesť tvrdenie, že je ľahko čitateľné.
- `origin`: `human`, `adapted` (upravené z uvedeného zdroja), `machine-translated`
  (strojový preklad; ostáva `draft`, kým ho neskontroluje človek).

Úplný popis polí je v `schema/slovnik.schema.json`.

## Ako slovník používa nástroj

Skill easy-to-read (Claude Code) má `scripts/dictionary.py`. Pri písaní ľahko čitateľného
textu spustí `lookup`, ktorý najskôr stiahne `manifest.json` z tohto repozitára, porovná
odtlačky sha256 s lokálnymi kópiami a stiahne len zmenené súbory (najviac raz za deň,
offline pracuje s lokálnou kópiou). Potom vypíše, ktoré slová v texte slovník vysvetľuje,
a autor vysvetlenie prevezme alebo upraví. Vlastné heslá si autor ukladá do súkromnej
vrstvy `user` a môže ich navrhnúť sem (`dictionary.py promote <slovo> --issue`).

Iný nástroj potrebuje len HTTPS a JSON: stiahnuť `manifest.json`, porovnať `sha256`,
stiahnuť `slovniky/*.json`.

## Ako prispieť

Pozrite [CONTRIBUTING.md](CONTRIBUTING.md). V skratke: nové slovo navrhnete cez formulár
„Navrhnúť slovo“ v Issues (bez znalosti gitu) alebo pull requestom, ktorý upraví
`slovniky/verejna-sprava-sk.json` a prejde `scripts/validate.py`.

## Licencie

- `slovniky/verejna-sprava-sk.json`: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Predbežne; po rozhodnutí MIRRI sa môže zmeniť (napríklad na CC0). Rozhoduje blok
  `licence` v súbore.
- `slovniky/hurraki-sk.json`: odvodené dielo z Hurraki – Lexikon für Leichte Sprache
  ([CC BY-SA 3.0 DE](https://creativecommons.org/licenses/by-sa/3.0/de/)), preto ostáva
  pod [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Každé heslo nesie
  adresu a revíziu pôvodného článku.
- Skripty v `scripts/`: MIT.

Pozri [LICENSE](LICENSE).

## Plán

1. Overovací prototyp (teraz): základ z komisar.sk, prvá dávka Hurraki, nástroj.
2. Po schválení MIRRI: MIRRI oficiálne osloví Úrad komisára, naklonuje repozitár
   a pozve ďalších odborníkov a organizácie ľudí s mentálnym znevýhodnením.
3. Overovanie hesiel čitateľmi (`reader-checked`), ďalšie domény (sociálne dávky,
   zdravotníctvo, dane, doprava), český a anglický slovník podľa rovnakej schémy.
