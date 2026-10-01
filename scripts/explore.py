#!/usr/bin/env python3
"""Zwiedza e-Stołówkę po zalogowaniu i szuka strony z jadłospisem.

Uruchom lokalnie, żeby sprawdzić, pod jakim adresem Twoja szkoła trzyma
jadłospis i czy parser integracji go rozumie. Hasło czytane jest z zmiennych
środowiskowych albo pytane interaktywnie — nigdy nie trafia do repozytorium.

    pip install -r requirements-test.txt
    cp .env.example .env    # i wpisz swoje dane
    python3 scripts/explore.py

Zapisuje każdą odwiedzoną stronę do katalogu dump/ (jest w .gitignore).
Uwaga: zapisany HTML może zawierać dane Twojego dziecka — przejrzyj go, zanim
komukolwiek wyślesz.
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

# Parser ładujemy bez Home Assistanta — tym samym loaderem, co testy.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from conftest import load_component

load_component()

from e_stolowka_standalone.api import LocaClient, parse_menu  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "dump"
ENV_FILE = ROOT / ".env"
MAX_PAGES = 40


def load_env() -> None:
    """Wczytaj .env do os.environ, nie nadpisując już ustawionych zmiennych.

    Własny parser zamiast python-dotenv, żeby skrypt nie wymagał dodatkowej
    zależności poza tym, czego potrzebuje sama integracja.
    """
    if not ENV_FILE.is_file():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _slug(url: str) -> str:
    """Nazwa pliku dla zrzutu strony."""
    path = urlparse(url).path.strip("/") or "index"
    query = urlparse(url).query
    name = f"{path}__{query}" if query else path
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:120] + ".html"


async def main() -> int:
    """Zaloguj się, przejdź po linkach i wypisz, gdzie jest jadłospis."""
    load_env()
    base = os.environ.get("STOLOWKA_URL", "https://sobolewosp.loca.pl")
    email = os.environ.get("STOLOWKA_EMAIL") or input("E-mail: ").strip()
    password = os.environ.get("STOLOWKA_PASSWORD") or getpass.getpass("Hasło: ")

    DUMP.mkdir(exist_ok=True)
    async with aiohttp.ClientSession() as session:
        client = LocaClient(session, base, email, password)
        print(f"Logowanie do {base} ...")
        await client.async_login()
        print("Zalogowano.\n")

        host = urlparse(base).hostname
        queue: list[str] = [base + "/"]
        seen: set[str] = set()
        found: list[tuple[str, int]] = []

        while queue and len(seen) < MAX_PAGES:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)

            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(url, timeout=timeout) as resp:
                    if "html" not in resp.headers.get("content-type", ""):
                        continue
                    html = await resp.text()
            except (aiohttp.ClientError, TimeoutError) as err:
                print(f"  !  {url} -> {err}")
                continue

            (DUMP / _slug(url)).write_text(html, encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else "?"

            days = parse_menu(html)
            flag = f"JADŁOSPIS: {len(days)} dni" if days else ""
            print(f"  {url}  [{title}] {flag}")
            if days:
                found.append((url, len(days)))

            for link in soup.select("a[href]"):
                nxt = urljoin(url, str(link["href"])).split("#")[0]
                if urlparse(nxt).hostname == host and "wyloguj" not in nxt.lower():
                    queue.append(nxt)

        print(f"\nZrzuty stron: {DUMP}")
        if not found:
            print("Nie znaleziono strony, którą parser rozpoznaje jako jadłospis.")
            print("Przejrzyj zrzuty w dump/ i dopasuj parser w api.py.")
            return 1

        print("\nStrony z jadłospisem:")
        for url, count in sorted(found, key=lambda item: -item[1]):
            print(f"  {url}  ({count} dni)")
            menu_by_day = parse_menu((DUMP / _slug(url)).read_text())
            for day, menu in sorted(menu_by_day.items()):
                print(f"    {day}: {', '.join(menu.dishes)[:100]}")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
