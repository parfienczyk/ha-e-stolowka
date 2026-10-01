# Jak pomóc

Projekt powstał dla jednej szkoły, ale platforma **loca.pl** obsługuje ich wiele.
Najcenniejszy wkład to zgłoszenia i poprawki od rodziców z innych szkół — każda
publikuje jadłospis trochę inaczej.

## Zgłoszenia

- **Integracja nie znajduje jadłospisu w Twojej szkole** → szablon
  [„Moja szkoła nie działa"](.github/ISSUE_TEMPLATE/nowa_szkola.yml).
  Dołącz wynik `scripts/explore.py` i fragment HTML — bez tego trzeba zgadywać.
- **Coś działa inaczej niż w README** → szablon
  [„Błąd"](.github/ISSUE_TEMPLATE/bug_report.yml).

## Środowisko

Parser nie zależy od Home Assistanta, więc testy ruszają bez jego instalacji:

```bash
pip install -r requirements-test.txt
pytest tests/ -q
ruff check . && ruff format --check .
```

Testy ładują moduły integracji w obejściu `tests/conftest.py` — `__init__.py`
importuje Home Assistanta, a nie chcemy go ciągnąć po to, żeby sprawdzić
parsowanie HTML-a.

Chcesz sprawdzić wszystko razem z HA? Zainstaluj go w wirtualnym środowisku
(`pip install homeassistant`) i zaimportuj moduły z `custom_components/` —
to wyłapie użycie API, którego w danej wersji jeszcze nie ma.

## Rozpoznanie własnej szkoły

```bash
cp .env.example .env    # adres, e-mail, hasło
python3 scripts/explore.py
```

Skrypt loguje się, obchodzi linki, zapisuje strony do `dump/` i wypisuje, które
z nich rozpoznaje jako jadłospis. `.env` i `dump/` są w `.gitignore`.

> **Zrzuty zawierają dane Twojego dziecka** — imię, klasę, rozliczenia. Nie
> wrzucaj ich do repo ani do zgłoszeń. Jako fixture dawaj okrojony HTML.

## Zmiany w parserze

`custom_components/e_stolowka/api.py` to serce projektu:

| Element | Odpowiada za |
| --- | --- |
| `NEWS_PATHS` (`const.py`) | gdzie szukać listy aktualności |
| `_RE_MENU_LINK` | rozpoznanie wpisu z jadłospisem po adresie |
| `_parse_day_blocks` | układ akapitowy — nagłówek dnia + potrawy |
| `_parse_tables` | układ tabelaryczny |
| `_RE_DIET` | odcięcie wariantów dietetycznych |

**Każdy nowy układ strony dodawaj razem z testem.** Fixture'y leżą
w `tests/fixtures/` — krótki, anonimowy fragment prawdziwego HTML-a jest wart
więcej niż wymyślony znacznik, bo prawdziwy bywa dziwniejszy.

Przy ruszaniu rozpoznawania dat uważaj na dwie pułapki, które już raz ugryzły:
liczby w rodzaju `1.5 l` wyglądają jak data, a data bez roku czytana na przełomie
grudnia i stycznia trafia o rok obok.

## Styl

- `ruff` pilnuje formatowania i lintu — ustawienia w `ruff.toml`.
- Docstring w każdej funkcji, po polsku, w trybie orzekającym.
- Komentarz tłumaczy **dlaczego**, nie **co**. Jeśli kod wymaga komentarza
  wyjaśniającego, co robi, zwykle da się go napisać jaśniej.
