# e-Stołówka dla Home Assistanta

[![Walidacja](https://github.com/parfienczyk/ha-e-stolowka/actions/workflows/validate.yml/badge.svg)](https://github.com/parfienczyk/ha-e-stolowka/actions/workflows/validate.yml)
[![HACS: repozytorium własne](https://img.shields.io/badge/HACS-repozytorium%20w%C5%82asne-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Wersja](https://img.shields.io/github/v/release/parfienczyk/ha-e-stolowka?display_name=tag&sort=semver)](https://github.com/parfienczyk/ha-e-stolowka/releases)
[![Licencja: MIT](https://img.shields.io/badge/licencja-MIT-blue.svg)](LICENSE)

**Jadłospis szkolnej stołówki w Home Assistancie.** Integracja czyta menu
z platformy **e-Stołówka** ([loca.pl](https://loca.pl)) i udostępnia je jako encje:
na dziś, na jutro i na cały pobrany tydzień — razem z alergenami i wariantami
dietetycznymi.

```
sensor.e_stolowka_sobolewosp_jadlospis_na_dzis
  zupa barszcz czerwony (seler, mleko), naleśniki z serem i sosem
  jogurtowo-jagodowym (mleko, pszenica, jaja), Kompot, Owoc: nektarynka
```

> Projekt społecznościowy, niepowiązany z loca.pl ani z żadną szkołą.

## Jak to działa

Platforma loca.pl nie ma publicznego API, a jadłospis nie ma nawet własnego modułu —
szkoła publikuje go jako **wpisy w aktualnościach**, po jednym na tydzień, pod adresami
w rodzaju `/sites/jadlospis-280926-021026,1946`. Zakres dat zapisany jest w samym
adresie, więc integracja czyta listę aktualności, wybiera wpisy obejmujące dzisiejszą
datę (bieżący tydzień i następny, żeby „jutro" działało też w piątek) i tylko je pobiera.

Wszystko to jest za logowaniem, więc integracja loguje się tym samym formularzem co
przeglądarka i trzyma sesję w ciasteczkach. Gdy sesja wygaśnie — loguje się ponownie;
gdy hasło przestanie działać — Home Assistant poprosi o nowe (przepływ *reauth*).

W treści wpisu dni rozdzielone są akapitami w rodzaju **PONIEDZIAŁEK 28.09.26**,
a warianty bezglutenowe i bezmleczne oznaczone przedrostkiem `DIETA:` — parser
rozdziela je na osobną listę. Alergeny zostają w nazwach potraw. Gdyby inna szkoła
publikowała jadłospis w tabeli, parser poradzi sobie również z takim układem.

## Instalacja

### HACS (zalecane)

1. HACS → **Integracje** → menu ⋮ → **Custom repositories**
2. Dodaj `https://github.com/parfienczyk/ha-e-stolowka`, kategoria **Integration**
3. Zainstaluj **e-Stołówka (loca.pl)** i zrestartuj Home Assistanta

### Ręcznie

Skopiuj katalog `custom_components/e_stolowka` do `config/custom_components/`
w swojej instalacji i zrestartuj Home Assistanta.

## Konfiguracja

**Ustawienia → Urządzenia i usługi → Dodaj integrację → e-Stołówka**

| Pole | Opis |
| --- | --- |
| Adres e-Stołówki | np. `https://sobolewosp.loca.pl` |
| E-mail | ten sam, którym logujesz się jako rodzic |
| Hasło | hasło do konta rodzica |

Częstotliwość odświeżania zmienisz w **Opcjach** integracji (domyślnie raz na dobę,
zakres 1–24 godziny — jadłospis zmienia się rzadko, nie ma po co obciążać serwera szkoły).

## Encje

Encje nazywane są po szkole wziętej z adresu, np. dla `sobolewosp.loca.pl`:

| Encja | Stan | Atrybuty |
| --- | --- | --- |
| `sensor.e_stolowka_sobolewosp_jadlospis_na_dzis` | dania w jednej linii | `data`, `potrawy`, `dieta`, `jadlospis` |
| `sensor.e_stolowka_sobolewosp_jadlospis_na_jutro` | dania w jednej linii | `data`, `potrawy`, `dieta`, `jadlospis` |
| `sensor.e_stolowka_sobolewosp_jadlospis_tygodniowy` | liczba dni z menu | `poczatek_tygodnia`, `koniec_tygodnia`, `dni` |

Stan encji w Home Assistancie nie może przekroczyć 255 znaków, więc pełny jadłospis
zawsze znajdziesz w atrybutach — `potrawy` jako listę, `jadlospis` jako tekst,
`dieta` jako listę wariantów dietetycznych. Sensor tygodniowy trzyma wszystkie
pobrane dni w atrybucie `dni`, kluczowane datą.

W weekendy, święta i ferie żaden wpis nie obejmuje dzisiejszej daty — sensory dzienne
mają wtedy stan `unknown`, a `potrawy` są puste. Automatyzacje warto więc zabezpieczyć
warunkiem, jak w przykładzie niżej.

### Własna karta Lovelace (zalecane)

W katalogu [`lovelace/`](lovelace/) leży gotowa karta — bez kroku budowania,
bez `card_mod`, bez ograniczeń sanityzatora karty markdown. Wygląda jak karty
systemowe, sama rozpoznaje tryb ciemny i wyróżnia dzisiejszy dzień.

1. Skopiuj `lovelace/e-stolowka-card.js` do `config/www/`
2. **Ustawienia → Dashboardy → ⋮ → Zasoby → Dodaj zasób**
   URL `/local/e-stolowka-card.js`, typ **Moduł JavaScript**
3. Odśwież przeglądarkę twardo (`Ctrl/Cmd + Shift + R`)
4. Dodaj kartę — znajdziesz ją w wyszukiwarce jako **e-Stołówka**

Karta ma edytor wizualny: sensor wybierzesz z listy, resztę przełącznikami.
Przy dodawaniu sama podpowiada pierwszy pasujący sensor tygodniowy. YAML
poniżej jest więc opcjonalny — dla tych, którzy wolą konfigurację tekstową:

```yaml
type: custom:e-stolowka-card
entity: sensor.e_stolowka_sobolewosp_jadlospis_tygodniowy
title: Stołówka
range: week      # week (bieżący tydzień) | all (wszystko) | today
show_diet: false # pokaż warianty dietetyczne jako plakietki
compact: false   # ciaśniejsze odstępy, bez podtytułu
```

Alergeny z nawiasów karta wydziela sama i wyświetla przygaszone obok nazwy
dania. `entity` to sensor **tygodniowy** — on zawiera wszystkie pobrane dni.

> Karta nie instaluje się przez HACS razem z integracją: repozytorium HACS ma
> jedną kategorię, a ta jest ustawiona na `integration`.

### Przykład karty markdown

```yaml
type: markdown
title: Stołówka
content: |
  {% set dzis = state_attr('sensor.e_stolowka_sobolewosp_jadlospis_na_dzis', 'potrawy') %}
  {% set jutro = state_attr('sensor.e_stolowka_sobolewosp_jadlospis_na_jutro', 'potrawy') %}
  **Dziś:**

  {% if dzis %}- {{ dzis | join('\n- ') }}{% else %}_brak jadłospisu_{% endif %}

  **Jutro:**

  {% if jutro %}- {{ jutro | join('\n- ') }}{% else %}_brak jadłospisu_{% endif %}
```

Wariant dietetyczny pokażesz, czytając atrybut `dieta` zamiast `potrawy`.

> Użyj `content: |`, nie `content: >`. Składany blok YAML (`>`) skleja kolejne
> linie spacjami, przez co punkty listy zlewają się w jeden akapit z myślnikami
> w środku zdania.

Powyższy YAML wklej przez **Show code editor** w konfiguracji karty. Jeśli
wolisz wizualny edytor, w pole **Content** wklej samą treść — bez linii
`type:`, `title:` i `content: |` — i **dosuń ją do lewej krawędzi**. Listy
markdown muszą zaczynać się w pierwszej kolumnie: wcięcie zamienia punkt
w zagnieżdżony podpunkt, a nagłówek wciąga do poprzedniego punktu.

**Mniejszy tekst i kolory.** Karta markdown nie ma opcji rozmiaru czcionki,
a `style="..."` nic nie da: Home Assistant przepuszcza treść przez bibliotekę
[`xss`](https://github.com/leizongmin/js-xss) z domyślną białą listą, w której
`div`, `span` i `ul` mają **pustą listę dozwolonych atrybutów**. Przechodzą za to
`<small>` oraz `<font>` z atrybutami `color`, `size` i `face`:

```yaml
type: markdown
title: Stołówka
content: |
  {% set dzis = state_attr('sensor.e_stolowka_sobolewosp_jadlospis_na_dzis', 'potrawy') or [] %}
  {% set jutro = state_attr('sensor.e_stolowka_sobolewosp_jadlospis_na_jutro', 'potrawy') or [] %}
  <font size="2"><b><font color="tomato">Dziś:</font></b></font>
  <ul>
  {% for p in dzis %}<li><font size="2">{{ p }}</font></li>{% else %}<li><font size="2"><i>brak jadłospisu</i></font></li>{% endfor %}
  </ul>
  <font size="2"><b><font color="tomato">Jutro:</font></b></font>
  <ul>
  {% for p in jutro %}<li><font size="2">{{ p }}</font></li>{% else %}<li><font size="2"><i>brak jadłospisu</i></font></li>{% endfor %}
  </ul>
```

`size` przyjmuje wartości 1–7, gdzie 3 jest domyślna — `2` daje mniejszy tekst,
`1` najmniejszy. Zamiast tego można użyć `<small>`, a `<small><small>` zmniejsza
dwustopniowo. Ta wersja jest też odporna na wcięcia, bo nie korzysta z list
markdown.

Tytuł karty pozostaje duży — to nagłówek, nie treść. Zmniejszysz go tylko przez
[card_mod](https://github.com/thomasloven/lovelace-card-mod) (HACS → Frontend):

```yaml
card_mod:
  style: |
    ha-card { font-size: 13px; }
    ha-card .card-header { font-size: 20px; padding-bottom: 4px; }
```

### Przykład karty tygodniowej

Sensor tygodniowy trzyma w atrybucie `dni` słownik `data → {potrawy, dieta,
jadlospis}`, kluczowany datą ISO. Integracja pobiera bieżący tydzień i następny,
żeby „jutro" działało także w piątek, więc karta filtruje dni do bieżącego
tygodnia. Dzisiejszy dzień jest wyróżniony kolorem:

```yaml
type: markdown
title: Jadłospis tygodniowy
content: |
  {% set dni = state_attr('sensor.e_stolowka_sobolewosp_jadlospis_tygodniowy', 'dni') or {} %}
  {% set nazwy = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela'] %}
  {% set dzis = now().date() %}
  {% set od = (dzis - timedelta(days=dzis.weekday())).isoformat() %}
  {% set do = (dzis + timedelta(days=6 - dzis.weekday())).isoformat() %}
  {% for data, menu in dni.items() if od <= data <= do %}
  {% set d = data | as_datetime %}
  <font size="2"><b><font color="{{ 'tomato' if data == dzis.isoformat() else 'cornflowerblue' }}">{{ nazwy[d.weekday()] }} {{ d.strftime('%d.%m') }}</font></b><br>
  {% for p in menu.potrawy %}• {{ p }}<br>{% endfor %}</font>
  {% else %}
  <font size="2"><i>Brak jadłospisu na ten tydzień.</i></font>
  {% endfor %}
```

Żeby pokazać oba pobrane tygodnie, usuń warunek `if od <= data <= do` z pętli.
Warianty dietetyczne pokażesz, zamieniając `menu.potrawy` na `menu.dieta`.

**Odstępy między wierszami.** `line-height` jest właściwością wyłącznie CSS-ową,
więc bez `card_mod` nie da się jej zmienić. Powyższa karta używa jednak `<br>`
zamiast `<ul>`, co usuwa marginesy elementów listy — a to one odpowiadają za
większość luzu. Pełną kontrolę daje dopiero
[card_mod](https://github.com/thomasloven/lovelace-card-mod):

```yaml
card_mod:
  style: |
    ha-card { line-height: 1.15; }
    ha-card .card-header { font-size: 20px; line-height: 1.2; padding-bottom: 4px; }
```

### Przykład automatyzacji

```yaml
automation:
  - alias: Jadłospis na jutro wieczorem
    triggers:
      - trigger: time
        at: "19:00:00"
    conditions:
      - condition: template
        value_template: >
          {{ state_attr('sensor.e_stolowka_sobolewosp_jadlospis_na_jutro', 'potrawy') | length > 0 }}
    actions:
      - action: notify.persistent_notification
        data:
          title: Jutro w stołówce
          message: "{{ state_attr('sensor.e_stolowka_sobolewosp_jadlospis_na_jutro', 'jadlospis') }}"
```

## Inna szkoła na loca.pl

Integracja nie jest przywiązana do jednej szkoły — wystarczy podać adres swojej.
Jeśli jadłospis nie zostanie znaleziony, to znaczy, że Twoja szkoła trzyma go pod
inną ścieżką albo w innym układzie HTML. Pomoże skrypt diagnostyczny:

```bash
pip install -r requirements-test.txt
cp .env.example .env    # wpisz adres szkoły, e-mail i hasło
python3 scripts/explore.py
```

`.env` jest w `.gitignore`. Zamiast pliku możesz podać zmienne środowiskowe
(`STOLOWKA_URL`, `STOLOWKA_EMAIL`, `STOLOWKA_PASSWORD`) — mają pierwszeństwo.
Bez hasła skrypt zapyta o nie interaktywnie.

Skrypt loguje się, przechodzi po linkach, zapisuje strony do `dump/` (katalog jest
w `.gitignore`) i wypisuje, które z nich parser rozpoznaje jako jadłospis. Jeśli lista
aktualności Twojej szkoły jest pod innym adresem, dopisz go do `NEWS_PATHS`
w `custom_components/e_stolowka/const.py`; jeśli wpisy nazywają się inaczej niż
`jadlospis-DDMMYY-DDMMYY,id`, trzeba poszerzyć wzorzec `_RE_MENU_LINK` w `api.py`.
Tak czy inaczej — otwórz [zgłoszenie](https://github.com/parfienczyk/ha-e-stolowka/issues),
dodamy obsługę na stałe.

> Zrzuty w `dump/` mogą zawierać dane Twojego dziecka. Przejrzyj je, zanim gdziekolwiek wyślesz.

## Rozwój

```bash
pip install -r requirements-test.txt
pytest tests/ -q      # testy parsera, nie wymagają Home Assistanta
ruff check . && ruff format --check .
```

## Prywatność

Dane logowania trafiają wyłącznie na serwer Twojej szkoły i są przechowywane
w konfiguracji Home Assistanta na Twoim urządzeniu. Każdy wpis konfiguracyjny ma
własną sesję i własne ciasteczka. Integracja nie wysyła niczego nigdzie indziej
i nie zbiera telemetrii — szczegóły w [SECURITY.md](SECURITY.md).

## Dokumenty

- [CONTRIBUTING.md](CONTRIBUTING.md) — jak pomóc, jak uruchomić testy, jak dodać obsługę kolejnej szkoły
- [SECURITY.md](SECURITY.md) — co integracja robi z danymi logowania i czego nie wysyłać publicznie
- [CHANGELOG.md](CHANGELOG.md) — historia zmian

## Licencja

[MIT](LICENSE)

Jeśli ta integracja oszczędza Ci porannego pytania „co dziś na obiad?" —
zostaw gwiazdkę. To cała zapłata, jakiej projekt oczekuje.
