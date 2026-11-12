"""Testy publicznej strony szkoły jako głównego źródła jadłospisu."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from aiohttp import ClientError
from e_stolowka_standalone.api import (
    LocaAuthError,
    LocaClient,
    LocaConnectionError,
    LocaParseError,
    MenuDay,
    is_valid_menu_url,
    merge_menus,
    parse_menu,
    public_menu_url,
)
from test_client import FakeResponse, FakeSession

FIXTURES = Path(__file__).parent / "fixtures"
SCHOOL_PAGE = (FIXTURES / "jadlospis_szkola.html").read_text(encoding="utf-8")

BASE = "https://szkola.loca.pl"
MENU_URL = "https://szkola.example/jadlospis/"
TODAY = date(2026, 11, 3)
MONDAY = date(2026, 11, 2)
THURSDAY = date(2026, 11, 5)
NEXT_MONDAY = date(2026, 11, 9)

LOCA_POST = f"{BASE}/sites/jadlospis-051126-091126,2000"
LOCA_PAGES = {
    f"{BASE}/sites/zobacz_wiadomosci": (
        f'<body class="logged"><main><a href="{LOCA_POST}">Czytaj więcej</a>'
        "</main></body>"
    ),
    LOCA_POST: (
        '<body class="logged"><main>'
        "<p><strong>CZWARTEK 05.11.26</strong></p><p>zupa z e-Stołówki</p>"
        "<p><strong>PONIEDZIAŁEK 09.11.26</strong></p><p>zupa na przyszły tydzień</p>"
        "</main></body>"
    ),
}


class SchoolSession(FakeSession):
    """Strona szkoły jest publiczna, więc odpowiada też bez logowania."""

    def __init__(self, school_page: str | None, **kwargs: Any) -> None:
        """Ustaw stronę szkoły; None oznacza, że serwer szkoły nie odpowiada."""
        super().__init__(LOCA_PAGES, **kwargs)
        self.school_page = school_page

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Obsłuż stronę szkoły, a resztę przekaż do e-Stołówki."""
        if url != MENU_URL:
            return super().get(url, **kwargs)
        self.calls.append(kwargs)
        self.requested.append(url)
        if self.school_page is None:
            raise ClientError("serwer szkoły nie odpowiada")
        return FakeResponse(self.school_page)


class BrokenLocaSession(SchoolSession):
    """Serwer loca.pl nie odpowiada, strona szkoły działa."""

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Odrzuć wszystko poza stroną szkoły."""
        if url != MENU_URL:
            raise ClientError("serwer loca.pl nie odpowiada")
        return super().get(url, **kwargs)


class PdfResponse(FakeResponse):
    """Plik binarny: aiohttp nie potrafi odczytać go jako tekstu."""

    async def text(self) -> str:
        """Zachowaj się jak aiohttp dla PDF-a bez kodowania znaków."""
        raise UnicodeDecodeError("utf-8", b"\xe2\xe3", 0, 1, "invalid continuation")


class PdfSchoolSession(SchoolSession):
    """Adres strony szkoły wskazuje PDF zamiast strony HTML."""

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Zwróć PDF dla strony szkoły."""
        if url == MENU_URL:
            return PdfResponse("")
        return super().get(url, **kwargs)


def _client(session: FakeSession, menu_url: str | None = MENU_URL) -> LocaClient:
    """Klient z ustawioną stroną szkoły."""
    return LocaClient(session, BASE, "rodzic@example.com", "tajne", menu_url)


def _combined(client: LocaClient) -> tuple[dict[date, MenuDay], Exception | None]:
    """Pobierz jadłospis z obu źródeł."""
    return asyncio.run(client.async_get_combined_menu(TODAY))


def test_sidebar_does_not_leak_into_last_day() -> None:
    """Boczne menu strony stoi w <main>, ale nie jest częścią jadłospisu."""
    days = parse_menu(SCHOOL_PAGE, TODAY)

    assert list(days) == [MONDAY, THURSDAY]
    assert days[THURSDAY].dishes == [
        "zupa pomidorowa z ryżem (seler, mleko)",
        "nuggetsy z kurczaka (pszenica, jaja)",
        "kasza kus kus (pszenica)",
        "mizeria (mleko)",
        "pieczywo mieszane (pszenica)",
        "napój: kompot",
        "owoc: śliwka",
    ]


def test_diet_lines_in_one_paragraph_are_separated() -> None:
    """Linia „DIETA:” po <br> trafia do diety, a nie do potraw."""
    days = parse_menu(SCHOOL_PAGE, TODAY)

    assert days[THURSDAY].diet == [
        "zupa pomidorowa z ryżem (seler)",
        "nuggetsy z kurczaka / indyka",
        "kasza jaglana",
        "ogórek z koperkiem i oliwą z oliwek",
    ]


def test_school_page_wins_and_loca_fills_the_rest() -> None:
    """Strona szkoły rozstrzyga o swoich dniach, e-Stołówka dokłada pozostałe."""
    days, loca_error = _combined(_client(SchoolSession(SCHOOL_PAGE)))

    assert loca_error is None
    assert list(days) == [MONDAY, THURSDAY, NEXT_MONDAY]
    assert days[THURSDAY].dishes[0] == "zupa pomidorowa z ryżem (seler, mleko)"
    assert days[NEXT_MONDAY].dishes == ["zupa na przyszły tydzień"]


def test_school_page_is_read_before_login() -> None:
    """Hasło nie trafia na stronę szkoły, a odpytanie jej nie wymaga logowania."""
    session = SchoolSession(SCHOOL_PAGE, logged_in=False)
    days, _ = _combined(_client(session))

    assert session.requested[0] == MENU_URL
    assert session.requested.count(f"POST {BASE}/") == 1
    assert not any(req.startswith(f"POST {MENU_URL}") for req in session.requested)
    assert NEXT_MONDAY in days


def test_school_page_request_has_a_timeout() -> None:
    """Żądanie do strony szkoły też ma limit czasu."""
    session = SchoolSession(SCHOOL_PAGE)
    _combined(_client(session))

    assert all(call.get("timeout") is not None for call in session.calls)


def test_loca_only_without_school_page() -> None:
    """Bez ustawionej strony integracja działa jak dotąd."""
    session = SchoolSession(SCHOOL_PAGE)
    days, loca_error = _combined(_client(session, menu_url=None))

    assert loca_error is None
    assert MENU_URL not in session.requested
    assert list(days) == [THURSDAY, NEXT_MONDAY]
    assert days[THURSDAY].dishes == ["zupa z e-Stołówki"]


def test_loca_used_when_school_page_is_down() -> None:
    """Niedziałająca strona szkoły nie zatrzymuje jadłospisu z e-Stołówki."""
    days, loca_error = _combined(_client(SchoolSession(None)))

    assert loca_error is None
    assert days[THURSDAY].dishes == ["zupa z e-Stołówki"]


def test_loca_used_when_school_page_has_no_menu() -> None:
    """Przebudowana strona szkoły też nie zatrzymuje jadłospisu z e-Stołówki."""
    days, loca_error = _combined(_client(SchoolSession("<main><p>Remont</p></main>")))

    assert loca_error is None
    assert days[THURSDAY].dishes == ["zupa z e-Stołówki"]


def test_loca_used_when_school_page_is_a_pdf() -> None:
    """PDF pod adresem strony szkoły nie wyłącza integracji."""
    days, loca_error = _combined(_client(PdfSchoolSession(SCHOOL_PAGE)))

    assert loca_error is None
    assert days[THURSDAY].dishes == ["zupa z e-Stołówki"]


def test_pdf_page_is_a_parse_error() -> None:
    """Komunikat mówi wprost, że pod adresem nie ma strony HTML."""
    client = _client(PdfSchoolSession(SCHOOL_PAGE))

    with pytest.raises(LocaParseError, match="nie jest stroną HTML"):
        asyncio.run(client.async_get_public_menu(TODAY))


def test_school_page_survives_loca_outage() -> None:
    """Gdy loca.pl leży, jadłospis zostaje, a błąd wraca do wywołującego."""
    days, loca_error = _combined(_client(BrokenLocaSession(SCHOOL_PAGE)))

    assert list(days) == [MONDAY, THURSDAY]
    assert isinstance(loca_error, LocaConnectionError)


def test_school_page_survives_bad_password() -> None:
    """Złe hasło nie gasi głównego źródła, ale jest zgłaszane do ponownego logowania."""
    session = SchoolSession(SCHOOL_PAGE, logged_in=False)
    session.login_succeeds = False
    days, loca_error = _combined(_client(session))

    assert list(days) == [MONDAY, THURSDAY]
    assert isinstance(loca_error, LocaAuthError)


def test_rejected_password_is_not_retried_while_school_page_works() -> None:
    """Złe hasło nie wraca na serwer szkoły przy każdym odświeżeniu."""
    session = SchoolSession(SCHOOL_PAGE, logged_in=False)
    session.login_succeeds = False
    client = _client(session)
    _combined(client)
    days, loca_error = _combined(client)

    assert session.login_attempts == 1
    assert list(days) == [MONDAY, THURSDAY]
    assert isinstance(loca_error, LocaAuthError)

    # Bez strony szkoły nie ma czego pokazać — błąd hasła wraca do Home Assistanta.
    session.school_page = None
    with pytest.raises(LocaAuthError):
        _combined(client)


def test_both_sources_down_raises() -> None:
    """Gdy zawiodą oba źródła, nie ma czego pokazać."""
    with pytest.raises(LocaConnectionError):
        _combined(_client(BrokenLocaSession(None)))


def test_bad_password_raises_without_school_page() -> None:
    """Bez strony szkoły złe hasło jest błędem jak dotąd."""
    session = SchoolSession(None, logged_in=False)
    session.login_succeeds = False

    with pytest.raises(LocaAuthError):
        _combined(_client(session))


def test_page_without_days_is_a_parse_error() -> None:
    """Strona bez jadłospisu daje komunikat wskazujący jej adres."""
    client = _client(SchoolSession("<main><p>Remont</p></main>"))

    with pytest.raises(LocaParseError, match=r"szkola\.example"):
        asyncio.run(client.async_get_public_menu(TODAY))


def test_merge_replaces_whole_day_and_sorts() -> None:
    """Dzień z głównego źródła zastępuje drugie w całości, zamiast się sumować."""
    primary = {THURSDAY: MenuDay(THURSDAY, ["zupa"], ["zupa dieta"])}
    secondary = {
        NEXT_MONDAY: MenuDay(NEXT_MONDAY, ["kotlet"]),
        THURSDAY: MenuDay(THURSDAY, ["Zupa"]),
        MONDAY: MenuDay(MONDAY, ["ryż"]),
    }
    merged = merge_menus(primary, secondary)

    assert list(merged) == [MONDAY, THURSDAY, NEXT_MONDAY]
    assert merged[THURSDAY] == primary[THURSDAY]


def test_known_school_gets_its_page_by_default() -> None:
    """Istniejące wpisy szkoły z Sobolewa dostają stronę bez zmiany opcji."""
    url = public_menu_url("https://SobolewoSP.loca.pl/", None)

    assert url == "https://szkolasobolewo.com/index.php/jadlospis-poniedzialek/"


def test_other_school_does_not_get_foreign_menu() -> None:
    """Inna szkoła na loca.pl nie dostaje cudzego jadłospisu."""
    assert public_menu_url("https://innaszkola.loca.pl", None) is None


def test_configured_page_wins_over_default() -> None:
    """Adres z opcji ma pierwszeństwo przed znanym."""
    assert public_menu_url("https://sobolewosp.loca.pl", MENU_URL) == MENU_URL


def test_empty_option_disables_school_page() -> None:
    """Puste pole w opcjach wyłącza stronę także szkole o znanym adresie."""
    assert public_menu_url("https://sobolewosp.loca.pl", "  ") is None


@pytest.mark.parametrize(
    ("url", "valid"),
    [
        (MENU_URL, True),
        ("http://szkola.example/", True),
        ("szkola.example/jadlospis", False),
        ("ftp://szkola.example/", False),
        ("file:///etc/passwd", False),
        ("https://", False),
        ("https://szkola.example:99999/jadlospis", False),
        ("https://szkola.example:abc/", False),
        ("http://[::1", False),
    ],
)
def test_menu_url_validation(url: str, valid: bool) -> None:
    """Opcje przyjmują tylko pełne adresy http(s)."""
    assert is_valid_menu_url(url) is valid
