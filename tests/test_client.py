"""Testy klienta: wybór właściwego tygodnia i odnawianie wygasłej sesji."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any, Self

import pytest
from e_stolowka_standalone.api import LocaAuthError, LocaClient, LocaParseError

BASE = "https://szkola.loca.pl"
FIXTURES = Path(__file__).parent / "fixtures"

LOGIN_PAGE = (
    '<body class="unlogged"><form>'
    '<input type="hidden" name="token" value="tok123">'
    '<input type="hidden" name="action" value="zaloguj">'
    "</form></body>"
)

MENU_28 = f"{BASE}/sites/jadlospis-280926-021026,1946"
MENU_21 = f"{BASE}/sites/jadlospis-210926-250926,1931"

NEWS = f"""<body class="logged"><main>
  <a href="{MENU_21}">Czytaj więcej</a>
  <a href="{MENU_28}">Czytaj więcej</a>
</main></body>"""


def _menu_page(weekday: str, day: str) -> str:
    """Minimalny wpis z jadłospisem na jeden dzień."""
    return (
        '<body class="logged"><main>'
        f"<p><strong>{weekday} {day}</strong></p><p>zupa pomidorowa</p>"
        "</main></body>"
    )


PAGES = {
    f"{BASE}/sites/zobacz_wiadomosci": NEWS,
    MENU_21: _menu_page("PONIEDZIAŁEK", "21.09.26"),
    MENU_28: _menu_page("PONIEDZIAŁEK", "28.09.26"),
}


class FakeResponse:
    """Odpowiedź HTTP udająca aiohttp."""

    def __init__(self, body: str) -> None:
        """Zapamiętaj treść odpowiedzi."""
        self._body = body

    async def __aenter__(self) -> Self:
        """Wejdź w kontekst."""
        return self

    async def __aexit__(self, *_: object) -> bool:
        """Wyjdź z kontekstu."""
        return False

    def raise_for_status(self) -> None:
        """Nic nie zgłasza — testujemy tylko odpowiedzi 200."""

    async def text(self) -> str:
        """Zwróć treść."""
        return self._body


class FakeSession:
    """Sesja HTTP zwracająca przygotowane strony i notująca żądania."""

    def __init__(self, pages: dict[str, str], *, logged_in: bool = True) -> None:
        """Ustaw strony i to, czy sesja jest uznawana za zalogowaną."""
        self.pages = pages
        self.logged_in = logged_in
        self.login_attempts = 0
        self.requested: list[str] = []
        self.login_succeeds = True

    def get(self, url: str, **_: Any) -> FakeResponse:
        """Zwróć stronę albo ekran logowania, gdy sesja wygasła."""
        self.requested.append(url)
        if not self.logged_in:
            return FakeResponse(LOGIN_PAGE)
        return FakeResponse(self.pages.get(url, '<body class="logged"></body>'))

    def post(self, url: str, **_: Any) -> FakeResponse:
        """Obsłuż logowanie."""
        self.requested.append(f"POST {url}")
        self.login_attempts += 1
        if self.login_succeeds:
            self.logged_in = True
            return FakeResponse('<body class="logged"></body>')
        return FakeResponse(LOGIN_PAGE)


def _client(session: FakeSession) -> LocaClient:
    """Klient wskazujący na atrapę sesji."""
    return LocaClient(session, BASE, "rodzic@example.com", "tajne")


def test_picks_week_covering_today() -> None:
    """Pobierany jest tydzień obejmujący dziś, a nie starszy wpis."""
    session = FakeSession(PAGES)
    days = asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))

    assert list(days) == [date(2026, 9, 28)]
    assert MENU_28 in session.requested
    assert MENU_21 not in session.requested


def test_fetches_current_and_next_week() -> None:
    """Przed rozpoczęciem tygodnia bierzemy bieżący i następny — dla „jutra”."""
    session = FakeSession(PAGES)
    days = asyncio.run(_client(session).async_get_menu(date(2026, 9, 22)))

    assert list(days) == [date(2026, 9, 21), date(2026, 9, 28)]


def test_falls_back_to_latest_post_during_holidays() -> None:
    """Gdy żaden tydzień nie obejmuje dziś, pokazujemy ostatni opublikowany."""
    session = FakeSession(PAGES)
    days = asyncio.run(_client(session).async_get_menu(date(2026, 12, 24)))

    assert list(days) == [date(2026, 9, 28)]
    assert MENU_21 not in session.requested


def test_relogs_when_session_expired() -> None:
    """Wygasła sesja powoduje ponowne logowanie i udane pobranie."""
    session = FakeSession(PAGES, logged_in=False)
    days = asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))

    assert session.login_attempts == 1
    assert list(days) == [date(2026, 9, 28)]


def test_bad_password_is_not_retried() -> None:
    """Odrzucone hasło zgłasza LocaAuthError bez kolejnych prób."""
    session = FakeSession(PAGES, logged_in=False)
    session.login_succeeds = False

    with pytest.raises(LocaAuthError):
        asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))
    assert session.login_attempts == 1


def test_missing_menu_posts_raise_parse_error() -> None:
    """Strona bez wpisów z jadłospisem daje komunikat wskazujący na przyczynę."""
    session = FakeSession({f"{BASE}/sites/zobacz_wiadomosci": '<body class="logged">'})

    with pytest.raises(LocaParseError, match="nie zawiera wpisów z jadłospisem"):
        asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))


def test_real_page_end_to_end() -> None:
    """Pełna ścieżka na prawdziwych zrzutach: lista aktualności → wpis."""
    school = "https://sobolewosp.loca.pl"
    session = FakeSession(
        {
            f"{school}/sites/zobacz_wiadomosci": (
                FIXTURES / "wiadomosci.html"
            ).read_text(),
            f"{school}/sites/jadlospis-280926-021026,1946": (
                FIXTURES / "jadlospis.html"
            ).read_text(),
        }
    )
    client = LocaClient(session, school, "rodzic@example.com", "tajne")
    days = asyncio.run(client.async_get_menu(date(2026, 9, 29)))

    assert list(days) == [date(2026, 9, 28), date(2026, 9, 29)]
    assert days[date(2026, 9, 29)].dishes[0] == "Skyr owocowy (mleko)"
