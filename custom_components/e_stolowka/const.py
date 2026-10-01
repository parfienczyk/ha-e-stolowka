"""Stałe integracji e-Stołówka (loca.pl)."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "e_stolowka"

CONF_BASE_URL = "base_url"
CONF_UPDATE_HOURS = "update_hours"

DEFAULT_BASE_URL = "https://sobolewosp.loca.pl"
DEFAULT_UPDATE_HOURS = 6
MIN_UPDATE_INTERVAL = timedelta(hours=1)

# Jadłospis publikowany jest jako wpis w aktualnościach, więc startujemy od
# listy aktualności. Strona główna też linkuje najnowsze wpisy — służy jako
# zapas, gdy szkoła ma inny adres listy.
NEWS_PATHS = (
    "/sites/zobacz_wiadomosci",
    "/",
)

# Ile kolejnych tygodni pobierać (bieżący + następny wystarcza na "jutro").
MAX_WEEKS = 2

ATTR_DATE = "data"
ATTR_DISHES = "potrawy"
ATTR_DIET = "dieta"
ATTR_MENU = "jadlospis"
ATTR_DAYS = "dni"
ATTR_WEEK_START = "poczatek_tygodnia"
ATTR_WEEK_END = "koniec_tygodnia"
