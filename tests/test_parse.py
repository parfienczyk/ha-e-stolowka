"""Testy parsera jadłospisu — na znaczniku, jakiego używa loca.pl."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from e_stolowka_standalone.api import MenuDay, find_menu_links, parse_menu

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 28)
BASE = "https://sobolewosp.loca.pl"

MONDAY = date(2026, 9, 28)
TUESDAY = date(2026, 9, 29)


@pytest.fixture
def menu() -> dict[date, MenuDay]:
    """Jadłospis z prawdziwego wpisu szkoły."""
    return parse_menu((FIXTURES / "jadlospis.html").read_text(), TODAY)


def test_splits_days_on_weekday_headers(menu: dict[date, MenuDay]) -> None:
    """Akapity z nazwą dnia i datą rozdzielają jadłospis na dni."""
    assert list(menu) == [MONDAY, TUESDAY]


def test_title_is_not_a_day(menu: dict[date, MenuDay]) -> None:
    """Nagłówek wpisu z zakresem dat nie tworzy fałszywego dnia."""
    assert date(2026, 10, 2) not in menu
    assert "jadłospis 28.09.26-02.10.26" not in menu[MONDAY].dishes


def test_dishes_keep_allergens(menu: dict[date, MenuDay]) -> None:
    """Alergeny zostają w nazwie potrawy."""
    assert menu[MONDAY].dishes == [
        "zupa krem z pieczarek (seler, mleko)",
        "spaghetti z sosem mięsno pomidorowym (pszenica durum, seler)",
        "Napój: sok tłoczony 100%",
    ]


def test_diet_variants_are_separated(menu: dict[date, MenuDay]) -> None:
    """Linie „DIETA:” idą do osobnej listy, bez przedrostka."""
    assert menu[MONDAY].diet == ["zupa krem z pieczarek (seler)"]
    assert menu[TUESDAY].diet == ["napój sojowy"]
    assert all("DIETA" not in dish for dish in menu[MONDAY].dishes)


def test_inline_tags_do_not_split_words(menu: dict[date, MenuDay]) -> None:
    """`(<em>m</em>leko)` to „(mleko)”, a nie „( m leko)”."""
    assert "Skyr owocowy (mleko)" in menu[TUESDAY].dishes


def test_entities_are_decoded(menu: dict[date, MenuDay]) -> None:
    """Encje HTML (`&oacute;`, `&nbsp;`) są rozkodowane."""
    assert "Napój: sok tłoczony 100%" in menu[MONDAY].dishes
    assert all("&" not in dish for dish in menu[MONDAY].dishes)


def test_text_and_summary(menu: dict[date, MenuDay]) -> None:
    """Tekst jest wielolinijkowy, streszczenie jednolinijkowe i krótkie."""
    day = menu[MONDAY]
    assert day.text.splitlines() == day.dishes
    assert "\n" not in day.summary
    assert len(day.summary) <= 255


def test_summary_is_truncated_to_entity_state_limit() -> None:
    """Stan encji w HA ma limit 255 znaków."""
    day = MenuDay(day=MONDAY, dishes=[f"danie numer {i}" for i in range(50)])
    assert len(day.summary) == 255
    assert day.summary.endswith("...")


def test_finds_menu_links_with_date_range() -> None:
    """Zakres tygodnia czytany jest z adresu wpisu, linki są posortowane."""
    links = find_menu_links((FIXTURES / "wiadomosci.html").read_text(), BASE)
    assert [(link.start, link.end) for link in links] == [
        (date(2026, 9, 21), date(2026, 9, 25)),
        (date(2026, 9, 28), date(2026, 10, 2)),
    ]
    assert links[1].url == f"{BASE}/sites/jadlospis-280926-021026,1946"


def test_ignores_posts_that_are_not_menus() -> None:
    """Inne aktualności nie są brane za jadłospis."""
    links = find_menu_links((FIXTURES / "wiadomosci.html").read_text(), BASE)
    assert all("przerwy-obiadowe" not in link.url for link in links)


def test_menu_link_covers() -> None:
    """Wpis obejmuje dni od początku do końca tygodnia włącznie."""
    link = find_menu_links((FIXTURES / "wiadomosci.html").read_text(), BASE)[1]
    assert link.covers(MONDAY)
    assert link.covers(date(2026, 10, 2))
    assert not link.covers(date(2026, 10, 3))


def test_page_without_menu_yields_nothing() -> None:
    """Strona bez jadłospisu daje pusty wynik, nie wyjątek."""
    assert parse_menu("<html><body><p>Brak danych</p></body></html>", TODAY) == {}
    assert find_menu_links("<html><body><a href='/platnik'>Rozliczenia</a>", BASE) == []


TABLE = """
<table>
  <tr><th>Data</th><th>Zupa</th><th>II danie</th></tr>
  <tr><td>11.05.2026</td><td>Żurek</td><td>Kotlet schabowy, ziemniaki</td></tr>
  <tr><td>12.05.2026</td><td>Pomidorowa<br>Pierogi ruskie</td>
      <td>DIETA: pierogi z serem</td></tr>
</table>
"""


def test_table_layout_fallback() -> None:
    """Gdy szkoła użyła tabeli, parser czyta wiersze."""
    days = parse_menu(TABLE, TODAY)
    assert list(days) == [date(2026, 5, 11), date(2026, 5, 12)]
    assert days[date(2026, 5, 11)].dishes == ["Żurek", "Kotlet schabowy, ziemniaki"]
    assert days[date(2026, 5, 12)].dishes == ["Pomidorowa", "Pierogi ruskie"]
    assert days[date(2026, 5, 12)].diet == ["pierogi z serem"]


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("01.01.2026", date(2026, 1, 1)),
        ("1-2-26", date(2026, 2, 1)),
        ("31.02.2026", None),
    ],
)
def test_date_formats(cell: str, expected: date | None) -> None:
    """Rozpoznawane formaty dat; niepoprawna data jest pomijana."""
    days = parse_menu(f"<table><tr><td>{cell}</td><td>Barszcz</td></tr></table>", TODAY)
    assert (next(iter(days)) if days else None) == expected


# ── Regresje z code review ───────────────────────────────────────────────────


def test_day_and_dishes_in_one_paragraph() -> None:
    """Układ z edytora WYSIWYG: cały dzień w jednym akapicie, dzielony <br>."""
    days = parse_menu(
        "<p><strong>PONIEDZIAŁEK 28.09.26</strong><br>zupa pomidorowa<br>kotlet</p>",
        TODAY,
    )
    assert list(days) == [MONDAY]
    assert days[MONDAY].dishes == ["zupa pomidorowa", "kotlet"]


def test_table_rows_for_one_day_are_merged() -> None:
    """Zupa i drugie danie w osobnych wierszach trafiają do tego samego dnia."""
    days = parse_menu(
        "<table>"
        "<tr><td>11.05.2026</td><td>Zupa</td><td>Żurek</td></tr>"
        "<tr><td>11.05.2026</td><td>II danie</td><td>Kotlet schabowy</td></tr>"
        "</table>",
        TODAY,
    )
    assert days[date(2026, 5, 11)].dishes == [
        "Zupa",
        "Żurek",
        "II danie",
        "Kotlet schabowy",
    ]


def test_quantity_is_not_mistaken_for_a_date() -> None:
    """Pogrubione „1.5 l" to nie 1 maja — bez roku nagłówek jest odrzucany."""
    assert (
        parse_menu("<p><strong>Zestaw 1.5 l soku</strong></p><p>cos</p>", TODAY) == {}
    )
    assert parse_menu("<table><tr><td>Mleko 1.5%</td><td>kakao</td></tr></table>") == {}


def test_weekday_without_date_uses_week_from_url() -> None:
    """Nagłówek „WTOREK" bez daty dostaje datę z tygodnia wpisu."""
    days = parse_menu(
        "<p><strong>WTOREK</strong></p><p>zupa B</p>", TODAY, week_start=MONDAY
    )
    assert list(days) == [TUESDAY]
    assert days[TUESDAY].dishes == ["zupa B"]


def test_weekday_without_date_or_context_does_not_leak() -> None:
    """Bez kontekstu tygodnia potrawy nie są dopisywane do poprzedniego dnia."""
    days = parse_menu(
        "<p><strong>PONIEDZIAŁEK 28.09.26</strong></p><p>zupa A</p>"
        "<p><strong>WTOREK</strong></p><p>zupa B</p>",
        TODAY,
    )
    assert days[MONDAY].dishes == ["zupa A"]
    assert "zupa B" not in days[MONDAY].dishes


@pytest.mark.parametrize(
    ("text", "read_on", "expected"),
    [
        ("28.12", date(2027, 1, 5), date(2026, 12, 28)),
        ("05.01", date(2026, 12, 28), date(2027, 1, 5)),
        ("15.06", date(2026, 6, 10), date(2026, 6, 15)),
    ],
)
def test_year_inference_picks_nearest(text: str, read_on: date, expected: date) -> None:
    """Data bez roku trafia w najbliższy rok — w obie strony przez przełom roku."""
    days = parse_menu(
        f"<p><strong>poniedziałek {text}</strong></p><p>zupa</p>", read_on
    )
    assert next(iter(days)) == expected
