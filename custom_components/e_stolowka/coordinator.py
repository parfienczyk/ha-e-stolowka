"""Cykliczne pobieranie jadłospisu."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import LocaAuthError, LocaClient, LocaError, MenuDay, public_menu_url
from .const import (
    CONF_BASE_URL,
    CONF_MENU_URL,
    CONF_UPDATE_HOURS,
    DEFAULT_UPDATE_HOURS,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type LocaConfigEntry = ConfigEntry[LocaCoordinator]


class LocaCoordinator(DataUpdateCoordinator[dict[date, MenuDay]]):
    """Trzyma jadłospis pobrany ze strony szkoły."""

    config_entry: LocaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: LocaConfigEntry,
        session: ClientSession,
    ) -> None:
        """Przygotuj koordynator na podstawie wpisu konfiguracyjnego.

        Sesja musi mieć własny słoik ciasteczek — uwierzytelnienie trzymane
        jest w ciasteczkach, więc sesja dzielona z innymi integracjami
        powodowałaby wzajemne wylogowywanie kont.
        """
        hours = entry.options.get(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=max(timedelta(hours=hours), MIN_UPDATE_INTERVAL),
        )
        self.client = LocaClient(
            session,
            entry.data[CONF_BASE_URL],
            entry.data[CONF_EMAIL],
            entry.data[CONF_PASSWORD],
            public_menu_url(
                entry.data[CONF_BASE_URL], entry.options.get(CONF_MENU_URL)
            ),
        )

    async def _async_update_data(self) -> dict[date, MenuDay]:
        """Pobierz jadłospis; klient sam loguje się do e-Stołówki, gdy trzeba."""
        try:
            days, loca_error = await self.client.async_get_combined_menu(
                dt_util.now().date()
            )
        except LocaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LocaError as err:
            raise UpdateFailed(str(err)) from err

        if loca_error is not None:
            _LOGGER.warning(
                "Jadłospis tylko ze strony szkoły, e-Stołówka zawiodła: %s", loca_error
            )
            # Prośba o nowe hasło bez wyjątku: ConfigEntryAuthFailed wyłączyłby
            # encje mimo działającego głównego źródła.
            if isinstance(loca_error, LocaAuthError):
                self.config_entry.async_start_reauth(self.hass)
        return days

    def day(self, offset: int = 0) -> MenuDay | None:
        """Zwróć jadłospis na dziś (offset 0), jutro (1) itd."""
        if not self.data:
            return None
        return self.data.get(dt_util.now().date() + timedelta(days=offset))
