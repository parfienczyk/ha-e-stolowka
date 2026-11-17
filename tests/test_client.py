"""Testy klienta: wybór właściwego tygodnia i odnawianie wygasłej sesji."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any, Self

import pytest
from e_stolowka_standalone.api import (
    MAX_PAGE_BYTES,
    LocaAuthError,
    LocaClient,
    LocaConnectionError,
    LocaParseError,
    LocaUrlError,
)

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


class _FakeContent:
    """Treść odpowiedzi z limitem odczytu, jak strumień aiohttp."""

    def __init__(self, body: bytes) -> None:
        """Zapamiętaj bajty."""
        self._body = body

    async def read(self, n: int = -1) -> bytes:
        """Zwróć co najwyżej n bajtów."""
        if n < 0:
            return self._body
        return self._body[:n]


class FakeResponse:
    """Odpowiedź HTTP udająca aiohttp."""

    def __init__(
        self,
        body: str,
        *,
        url: str = f"{BASE}/",
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Zapamiętaj treść odpowiedzi."""
        self.status = status
        self.headers = headers or {}
        self.url = url
        self.charset = "utf-8"
        self.content = _FakeContent(body.encode())

    async def __aenter__(self) -> Self:
        """Wejdź w kontekst."""
        return self

    async def __aexit__(self, *_: object) -> bool:
        """Wyjdź z kontekstu."""
        return False

    def raise_for_status(self) -> None:
        """Nic nie zgłasza — testujemy tylko odpowiedzi 200."""


class FakeSession:
    """Sesja HTTP zwracająca przygotowane strony i notująca żądania."""

    def __init__(self, pages: dict[str, str], *, logged_in: bool = True) -> None:
        """Ustaw strony i to, czy sesja jest uznawana za zalogowaną."""
        self.pages = pages
        self.logged_in = logged_in
        self.login_attempts = 0
        self.requested: list[str] = []
        self.calls: list[dict[str, Any]] = []
        self.login_succeeds = True
        self.redirects: dict[str, str] = {}

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Zwróć stronę albo ekran logowania, gdy sesja wygasła."""
        self.calls.append(kwargs)
        self.requested.append(url)
        if url in self.redirects:
            return FakeResponse(
                "", url=url, status=302, headers={"Location": self.redirects[url]}
            )
        if not self.logged_in:
            return FakeResponse(LOGIN_PAGE, url=url)
        body = self.pages.get(url, '<body class="logged"></body>')
        return FakeResponse(body, url=url)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        """Obsłuż logowanie."""
        self.calls.append(kwargs)
        self.requested.append(f"POST {url}")
        self.login_attempts += 1
        if self.login_succeeds:
            self.logged_in = True
            return FakeResponse('<body class="logged"></body>', url=url)
        return FakeResponse(LOGIN_PAGE, url=url)


def _client(session: FakeSession) -> LocaClient:
    """Klient wskazujący na atrapę sesji."""
    return LocaClient(session, BASE, "rodzic@example.com", "tajne")


def test_every_request_has_a_timeout() -> None:
    """Żądanie do szkoły nie zostaje bez limitu czasu."""
    session = FakeSession(PAGES)
    asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))

    assert session.calls
    assert all(call.get("timeout") is not None for call in session.calls)


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


def test_week_start_from_url_is_passed_to_parser() -> None:
    """Dzień bez daty w treści jest rozpoznany dzięki tygodniowi z adresu."""
    session = FakeSession(
        {
            f"{BASE}/sites/zobacz_wiadomosci": NEWS,
            MENU_28: (
                '<body class="logged"><main>'
                "<p><strong>ŚRODA</strong></p><p>zupa pomidorowa</p>"
                "</main></body>"
            ),
        }
    )
    days = asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))

    assert list(days) == [date(2026, 9, 30)]


def test_parse_error_wins_over_connection_error() -> None:
    """Gdy jedna ścieżka pada, a druga wczytuje się bez jadłospisu — mów o tym."""

    class PartlyBrokenSession(FakeSession):
        def get(self, url: str, **kwargs: Any) -> FakeResponse:
            if url.endswith("/sites/zobacz_wiadomosci"):
                raise LocaConnectionError("404")
            return super().get(url, **kwargs)

    session = PartlyBrokenSession({f"{BASE}/": '<body class="logged"></body>'})

    with pytest.raises(LocaParseError, match="nie zawiera wpisów z jadłospisem"):
        asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))


def test_http_base_url_is_rejected_before_any_request() -> None:
    """Hasło nie wychodzi, gdy adres szkoły nie jest https."""
    session = FakeSession(PAGES)

    with pytest.raises(LocaUrlError):
        LocaClient(session, "http://szkola.loca.pl", "rodzic@example.com", "tajne")
    assert session.requested == []


def test_off_host_redirect_is_not_followed() -> None:
    """Przekierowanie na inny host nie jest pobierane."""
    session = FakeSession(PAGES)
    session.redirects[MENU_28] = "http://192.168.1.1/secret"

    with pytest.raises(LocaConnectionError, match="spoza szkoły"):
        asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))
    assert all("192.168.1.1" not in url for url in session.requested)


def test_same_host_https_redirect_is_followed() -> None:
    """Przekierowanie na https tej samej szkoły jest odczytywane."""
    session = FakeSession(PAGES)
    target = f"{MENU_28}?ok=1"
    session.redirects[MENU_28] = target
    session.pages[target] = PAGES[MENU_28]

    days = asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))

    assert list(days) == [date(2026, 9, 28)]
    assert target in session.requested


def test_oversized_page_is_rejected() -> None:
    """Strona większa niż limit nie jest parsowana."""
    session = FakeSession(PAGES)
    session.pages[MENU_28] = "x" * (MAX_PAGE_BYTES + 1)

    with pytest.raises(LocaConnectionError, match="za duża"):
        asyncio.run(_client(session).async_get_menu(date(2026, 9, 30)))
