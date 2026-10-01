"""Klient e-Stołówki na platformie loca.pl.

Platforma nie ma API, a jadłospis nie ma własnego modułu — szkoła publikuje go
jako wpisy w aktualnościach, po jednym na tydzień, pod adresami w postaci
`/sites/jadlospis-280926-021026,1946` (zakres dat zapisany w samym adresie).
Klient loguje się formularzem rodzica, czyta listę aktualności, wybiera wpisy
obejmujące dzisiejszą datę i wyciąga z nich jadłospis.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

from aiohttp import ClientError, ClientSession, ClientTimeout
from bs4 import BeautifulSoup, Tag

from .const import MAX_WEEKS, NEWS_PATHS

_LOGGER = logging.getLogger(__name__)

TIMEOUT = ClientTimeout(total=30)

# Formularz logowania: POST na / z tokenem CSRF ukrytym w <input name="token">.
LOGIN_MODULE = "users"
LOGIN_ACTION = "zaloguj"

# Wpis z jadłospisem: /sites/jadlospis-<od DDMMYY>-<do DDMMYY>,<id>
_RE_MENU_LINK = re.compile(r"jadlospis-(\d{6})-(\d{6}),(\d+)", re.IGNORECASE)

_WEEKDAYS_PL = (
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "sobota",
    "niedziela",
)

# Nagłówek dnia, np. "PONIEDZIAŁEK 28.09.26".
_RE_DAY_HEADER = re.compile(rf"^({'|'.join(_WEEKDAYS_PL)})\b\s*(.*)$", re.IGNORECASE)

# Wariant dietetyczny dania, np. "DIETA: zupa krem z pieczarek (seler)".
_RE_DIET = re.compile(r"^dieta\s*:?\s*", re.IGNORECASE)

# Data w treści: 28.09.26, 28.09.2026, 28-09-2026.
_RE_DATE = re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?\b")

_BLOCK_TAGS = ("p", "li", "h2", "h3", "h4", "h5", "dd")

# Wiersze, które nie są potrawami.
_NOISE = re.compile(
    r"^(jadłospis|menu|data|dzień|dzien|alergeny|razem|suma|lp\.?|brak|"
    r"czytaj więcej|wstecz|kontynuuj)$",
    re.IGNORECASE,
)


class LocaError(Exception):
    """Błąd ogólny integracji."""


class LocaAuthError(LocaError):
    """Nieprawidłowy e-mail lub hasło."""


class LocaConnectionError(LocaError):
    """Nie udało się połączyć z serwerem."""


class LocaParseError(LocaError):
    """Zalogowano, ale nie znaleziono jadłospisu."""


@dataclass(slots=True)
class MenuDay:
    """Jadłospis na jeden dzień."""

    day: date
    dishes: list[str] = field(default_factory=list)
    diet: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Jadłospis podstawowy jako tekst wielolinijkowy."""
        return "\n".join(self.dishes)

    @property
    def summary(self) -> str:
        """Jednolinijkowe streszczenie mieszczące się w stanie encji (255 znaków)."""
        joined = ", ".join(self.dishes)
        return joined[:252] + "..." if len(joined) > 255 else joined


@dataclass(frozen=True, slots=True)
class MenuLink:
    """Wpis z jadłospisem na jeden tydzień."""

    url: str
    start: date
    end: date

    def covers(self, day: date) -> bool:
        """Czy wpis obejmuje podaną datę."""
        return self.start <= day <= self.end


class LocaClient:
    """Sesja rodzica w e-Stołówce."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        email: str,
        password: str,
    ) -> None:
        """Przygotuj klienta. Nie wykonuje żadnych żądań."""
        self._session = session
        self._base = base_url.rstrip("/")
        self._email = email
        self._password = password
        self._news_path: str | None = None

    def _url(self, path: str) -> str:
        """Zbuduj pełny URL ze ścieżki względnej."""
        return urljoin(self._base + "/", path.lstrip("/"))

    async def _fetch(self, path: str, data: dict[str, str] | None = None) -> str:
        """Pobierz stronę; POST, gdy podano dane formularza."""
        url = self._url(path)
        method = self._session.post if data else self._session.get
        try:
            async with method(url, data=data, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                return await resp.text()
        except ClientError as err:
            raise LocaConnectionError(f"Błąd połączenia z {url}: {err}") from err
        except TimeoutError as err:
            raise LocaConnectionError(f"Przekroczono czas odpowiedzi {url}") from err

    async def _async_csrf_token(self) -> str:
        """Pobierz token CSRF z formularza logowania."""
        soup = BeautifulSoup(await self._fetch("/"), "html.parser")
        token = soup.select_one('form input[name="token"]')
        if token is None or not token.get("value"):
            raise LocaParseError("Nie znaleziono tokenu w formularzu logowania")
        return str(token["value"])

    async def async_login(self) -> None:
        """Zaloguj się i zapisz sesję w ciasteczkach."""
        html = await self._fetch(
            "/",
            {
                "module": LOGIN_MODULE,
                "action": LOGIN_ACTION,
                "token": await self._async_csrf_token(),
                "a_user[email]": self._email,
                "a_user[haslo]": self._password,
                "submit": "Zaloguj",
            },
        )
        if _is_logged_out(html):
            raise LocaAuthError("Odrzucono logowanie — sprawdź e-mail i hasło")
        # Bez adresu e-mail: logi debug trafiają do publicznych zgłoszeń.
        _LOGGER.debug("Zalogowano w e-Stołówce (%s)", self._base)

    async def async_get_menu(self, today: date | None = None) -> dict[date, MenuDay]:
        """Zwróć jadłospis na bieżący i najbliższy tydzień, kluczowany datą.

        Loguje się ponownie, gdy sesja wygasła.
        """
        today = today or date.today()
        for attempt in (1, 2):
            try:
                html = await self._async_fetch_news()
                if _is_logged_out(html):
                    raise LocaAuthError("Lista aktualności wymaga logowania")
                return await self._async_collect(html, today)
            except LocaAuthError:
                if attempt == 2:
                    raise
                # Logowanie wywołane tutaj zgłosi własny LocaAuthError przy
                # błędnym haśle — i słusznie, bo ponawianie nic nie da.
                _LOGGER.debug("Sesja wygasła, loguję ponownie")
                self._news_path = None
                await self.async_login()
        raise LocaParseError("Nie udało się pobrać jadłospisu")

    async def _async_collect(self, news_html: str, today: date) -> dict[date, MenuDay]:
        """Wybierz aktualne wpisy z jadłospisem i scal ich treść."""
        links = find_menu_links(news_html, self._base)
        if not links:
            raise LocaParseError(
                "Na liście aktualności nie ma wpisów z jadłospisem — "
                "być może szkoła publikuje go inaczej"
            )

        # Wpisy są posortowane po dacie początkowej. Bierzemy tygodnie, które się
        # jeszcze nie skończyły; gdy nie ma żadnego, pokazujemy ostatni opublikowany.
        upcoming = [link for link in links if link.end >= today][:MAX_WEEKS]
        chosen = upcoming or links[-1:]

        days: dict[date, MenuDay] = {}
        for link in chosen:
            _LOGGER.debug(
                "Czytam jadłospis %s (%s - %s)", link.url, link.start, link.end
            )
            page = await self._fetch(link.url)
            # Sesja mogła wygasnąć już po pobraniu listy aktualności; bez tego
            # sprawdzenia strona logowania wyglądałaby jak pusty jadłospis.
            if _is_logged_out(page):
                raise LocaAuthError("Sesja wygasła przy czytaniu jadłospisu")
            days.update(parse_menu(page, today, link.start))

        if not days:
            raise LocaParseError(
                "Wpis z jadłospisem nie zawiera rozpoznawalnych dni: "
                + ", ".join(link.url for link in chosen)
            )
        return dict(sorted(days.items()))

    async def _async_fetch_news(self) -> str:
        """Pobierz listę aktualności; zapamiętuje działającą ścieżkę."""
        if self._news_path is not None:
            return await self._fetch(self._news_path)

        last_error: LocaError | None = None
        loaded = False
        for path in NEWS_PATHS:
            try:
                html = await self._fetch(path)
            except LocaConnectionError as err:
                last_error = err
                continue
            loaded = True
            if _is_logged_out(html) or find_menu_links(html, self._base):
                self._news_path = path
                return html

        # Rozróżniamy „nie dowieźliśmy żadnej strony” od „strony są, ale bez
        # jadłospisu”. Drugi przypadek zdarza się szkołom z innym układem serwisu
        # i ma pierwszeństwo nad błędem połączenia z pozostałych kandydatów —
        # inaczej 404 na jednej ścieżce zasłoniłby to, co naprawdę się stało.
        checked = ", ".join(NEWS_PATHS)
        if loaded:
            raise LocaParseError(
                f"Żadna ze stron ({checked}) nie zawiera wpisów z jadłospisem"
            )
        if last_error is not None:
            raise last_error
        raise LocaParseError(
            f"Nie znaleziono listy aktualności — sprawdzone ścieżki: {checked}"
        )


def _is_logged_out(html: str) -> bool:
    """Czy serwer zwrócił stronę dla niezalogowanego użytkownika."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if body is not None and "unlogged" in (body.get("class") or []):
        return True
    return soup.select_one('form input[value="zaloguj"]') is not None


def find_menu_links(html: str, base_url: str) -> list[MenuLink]:
    """Znajdź wpisy z jadłospisem, posortowane po dacie początkowej.

    Zakres dat czytamy z adresu wpisu, więc wybór właściwego tygodnia nie
    wymaga pobierania wszystkich wpisów.
    """
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base_url).hostname
    links: dict[str, MenuLink] = {}
    for anchor in soup.select("a[href]"):
        href = str(anchor["href"])
        match = _RE_MENU_LINK.search(href)
        if match is None:
            continue
        start, end = _slug_date(match.group(1)), _slug_date(match.group(2))
        if start is None or end is None or end < start:
            continue

        url = urljoin(base_url + "/", href)
        parts = urlparse(url)
        # Odnośniki pochodzą z treści serwisu, więc traktujemy je jak dane
        # niezaufane: bez tego sprawdzenia spreparowany wpis kazałby Home
        # Assistantowi odpytać dowolny host z sieci domowej użytkownika.
        if parts.scheme not in ("http", "https") or parts.hostname != host:
            _LOGGER.debug("Pomijam odnośnik spoza %s: %s", host, url)
            continue

        links[url] = MenuLink(url=url, start=start, end=end)
    return sorted(links.values(), key=lambda link: link.start)


def _slug_date(value: str) -> date | None:
    """Zinterpretuj datę zapisaną w adresie wpisu jako DDMMYY."""
    try:
        return datetime.strptime(value, "%d%m%y").date()
    except ValueError:
        return None


def parse_menu(
    html: str,
    today: date | None = None,
    week_start: date | None = None,
) -> dict[date, MenuDay]:
    """Wyciągnij jadłospis z treści wpisu.

    Dni rozdzielone są akapitami z nazwą dnia tygodnia i datą; wszystko między
    nagłówkami to potrawy. Gdy szkoła użyła tabeli, przechodzimy na parser tabel.
    `week_start` (data z adresu wpisu) pozwala rozpoznać dzień także wtedy, gdy
    w nagłówku jest sama nazwa dnia, bez daty.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script, style, nav, footer, header"):
        tag.decompose()
    for line_break in soup.find_all("br"):
        line_break.replace_with("\n")

    content = soup.select_one("main") or soup.body or soup
    days = _parse_day_blocks(content, today, week_start)
    if not days:
        days = _parse_tables(content, today)
    return dict(sorted(days.items()))


def _parse_day_blocks(
    content: Tag, today: date | None, week_start: date | None
) -> dict[date, MenuDay]:
    """Zbierz jadłospis z akapitów, dzielonych nagłówkami dni tygodnia."""
    days: dict[date, MenuDay] = {}
    current: MenuDay | None = None

    for block in content.find_all(_BLOCK_TAGS):
        # Pomiń kontenery — ich treść przeczytamy z elementów wewnętrznych.
        if block.find(_BLOCK_TAGS):
            continue

        line = _text(block)
        if not line:
            continue

        # Edytory WYSIWYG wstawiają cały dzień w jeden akapit, rozdzielony <br>,
        # więc nagłówka szukamy w pierwszej linii, a resztę traktujemy jak potrawy.
        header, _, rest = line.partition("\n")
        day, is_header = _day_header(block, header, today, week_start)
        if is_header:
            # Nagłówek dnia bez rozpoznanej daty nie może dziedziczyć poprzedniego
            # dnia — lepiej pominąć te potrawy niż przypisać je do złej daty.
            current = days.setdefault(day, MenuDay(day=day)) if day else None
            if current is not None and rest:
                _add_dish(current, rest)
            continue

        if current is not None:
            _add_dish(current, line)

    return {day: menu for day, menu in days.items() if menu.dishes or menu.diet}


def _day_header(
    block: Tag, line: str, today: date | None, week_start: date | None
) -> tuple[date | None, bool]:
    """Zwróć (datę, czy-to-nagłówek) dla pierwszej linii akapitu.

    Nazwa dnia tygodnia jest wiarygodnym separatorem, więc uznajemy ją za
    nagłówek nawet bez czytelnej daty — wtedy datę wyliczamy z tygodnia wpisu.
    """
    match = _RE_DAY_HEADER.match(line)
    if match is not None:
        rest = match.group(2)
        day = _parse_date(rest or line, today)
        if day is None and week_start is not None:
            day = _weekday_in_week(week_start, match.group(1).lower())
        return day, True

    # Nagłówek bez nazwy dnia musi mieć pełną datę z rokiem, inaczej pogrubiona
    # linia w rodzaju "Zestaw 1.5 l soku" udawałaby 1 maja.
    if _is_bold(block) and len(_RE_DATE.findall(line)) == 1:
        day = _parse_date(line, today, require_year=True)
        if day is not None:
            return day, True
    return None, False


def _weekday_in_week(week_start: date, weekday: str) -> date | None:
    """Wylicz datę dnia tygodnia w tygodniu rozpoczętym podaną datą."""
    try:
        index = _WEEKDAYS_PL.index(weekday)
    except ValueError:
        return None
    return week_start + timedelta(days=index - week_start.weekday())


def _is_bold(block: Tag) -> bool:
    """Czy cała treść akapitu jest pogrubiona."""
    bold = block.find_all(["strong", "b"])
    if not bold:
        return False
    return _clean("".join(tag.get_text("") for tag in bold)) == _text(block)


def _add_dish(menu: MenuDay, line: str) -> None:
    """Dopisz linię do potraw albo do wariantu dietetycznego."""
    for part in line.split("\n"):
        part = _clean(part).strip(" -•*;,")
        if len(part) < 3 or _NOISE.match(part) or part.lower() in _WEEKDAYS_PL:
            continue
        if (diet := _RE_DIET.sub("", part)) != part:
            if diet and diet not in menu.diet:
                menu.diet.append(diet)
        elif part not in menu.dishes:
            menu.dishes.append(part)


def _parse_tables(content: Tag, today: date | None) -> dict[date, MenuDay]:
    """Zbierz jadłospis z wierszy tabel — układ używany przez część szkół.

    Kilka wierszy może opisywać ten sam dzień (osobno zupa, osobno drugie
    danie), dlatego wiersze scalamy, a nie nadpisujemy.
    """
    days: dict[date, MenuDay] = {}
    for row in content.select("tr"):
        cells = [_text(cell) for cell in row.select("th, td")]
        cells = [cell for cell in cells if cell]
        if not cells:
            continue

        dates = [_parse_date(cell, today, require_year=True) for cell in cells]
        day = next(filter(None, dates), None)
        if day is None:
            continue

        menu = days.setdefault(day, MenuDay(day=day))
        for cell, cell_date in zip(cells, dates, strict=True):
            if cell_date is None:
                _add_dish(menu, cell)

    return {day: menu for day, menu in days.items() if menu.dishes or menu.diet}


def _text(tag: Tag) -> str:
    """Odczytaj tekst elementu, nie rozrywając wyrazów łamanych znacznikami.

    `get_text(" ")` zamieniłoby `(<em>m</em>leko)` na `( m leko)`, dlatego tagi
    inline sklejamy bez separatora, a zagnieżdżone bloki rozdzielamy nową linią.
    """
    separator = "\n" if tag.find(_BLOCK_TAGS) else ""
    return _clean(tag.get_text(separator))


def _clean(text: str) -> str:
    """Znormalizuj biele znaki, zachowując podział na linie."""
    lines = (re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _parse_date(
    text: str, today: date | None = None, *, require_year: bool = False
) -> date | None:
    """Zinterpretuj datę; rok uzupełnia z bieżącego, gdy go brakuje.

    `require_year` odrzuca zapisy bez roku — potrzebne tam, gdzie nie ma innego
    kontekstu i liczby w rodzaju „1.5 l" wyglądałyby jak data.
    """
    match = _RE_DATE.search(text)
    if match is None:
        return None

    today = today or date.today()
    day, month, year = match.group(1), match.group(2), match.group(3)
    if year is None:
        if require_year:
            return None
        return _nearest_year(today, int(month), int(day))

    value = int(year)
    return _safe_date(value + 2000 if value < 100 else value, int(month), int(day))


def _nearest_year(today: date, month: int, day: int) -> date | None:
    """Dobierz rok tak, by data wypadła najbliżej dzisiejszej.

    Styczniowy jadłospis czytany w grudniu należy do następnego roku, a grudniowy
    czytany w styczniu — do poprzedniego.
    """
    candidates = (_safe_date(today.year + offset, month, day) for offset in (-1, 0, 1))
    valid = [candidate for candidate in candidates if candidate is not None]
    if not valid:
        return None
    return min(valid, key=lambda candidate: abs((candidate - today).days))


def _safe_date(year: int, month: int, day: int) -> date | None:
    """Zbuduj datę, zwracając None dla niepoprawnych wartości."""
    try:
        return date(year, month, day)
    except ValueError:
        return None
