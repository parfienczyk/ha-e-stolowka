"""Integracja e-Stołówka (loca.pl) dla Home Assistanta."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .coordinator import LocaConfigEntry, LocaCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: LocaConfigEntry) -> bool:
    """Skonfiguruj wpis: zaloguj się i pobierz pierwszy jadłospis."""
    # Własna sesja na wpis: ciasteczka logowania nie mogą mieszać się
    # z sesją dzieloną przez pozostałe integracje.
    session = async_create_clientsession(hass)
    entry.async_on_unload(session.close)

    coordinator = LocaCoordinator(hass, entry, session)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LocaConfigEntry) -> bool:
    """Usuń encje wpisu."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: LocaConfigEntry) -> None:
    """Przeładuj wpis po zmianie opcji."""
    await hass.config_entries.async_reload(entry.entry_id)
