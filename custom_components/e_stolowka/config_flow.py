"""Konfiguracja integracji z poziomu interfejsu Home Assistanta."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import LocaAuthError, LocaClient, LocaConnectionError, LocaError
from .const import (
    CONF_BASE_URL,
    CONF_UPDATE_HOURS,
    DEFAULT_BASE_URL,
    DEFAULT_UPDATE_HOURS,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


async def _async_validate(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Sprawdź, czy podane dane pozwalają się zalogować.

    Sesja jednorazowa, żeby ciasteczka z próbnego logowania nie zostawały
    w sesji dzielonej przez pozostałe integracje.
    """
    session = async_create_clientsession(hass)
    try:
        client = LocaClient(
            session,
            data[CONF_BASE_URL],
            data[CONF_EMAIL],
            data[CONF_PASSWORD],
        )
        await client.async_login()
    finally:
        await session.close()


class LocaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Kreator dodawania szkolnej stołówki."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Zapytaj o adres szkoły i dane rodzica."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = urlparse(user_input[CONF_BASE_URL]).hostname or ""
            school = host.split(".")[0] or "e-Stołówka"
            await self.async_set_unique_id(f"{host}::{user_input[CONF_EMAIL].lower()}")
            self._abort_if_unique_id_configured()

            errors = await self._async_try_login(user_input)
            if not errors:
                return self.async_create_entry(title=school, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Rozpocznij ponowne uwierzytelnienie po zmianie hasła."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Zapytaj o nowe hasło dla istniejącego wpisu."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            errors = await self._async_try_login(data)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={CONF_EMAIL: entry.data[CONF_EMAIL]},
            errors=errors,
        )

    async def _async_try_login(self, data: Mapping[str, Any]) -> dict[str, str]:
        """Zwróć słownik błędów formularza; pusty, gdy logowanie się udało."""
        try:
            await _async_validate(self.hass, data)
        except LocaAuthError:
            return {"base": "invalid_auth"}
        except LocaConnectionError:
            return {"base": "cannot_connect"}
        except LocaError:
            return {"base": "unknown"}
        return {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> LocaOptionsFlow:
        """Udostępnij ekran opcji."""
        return LocaOptionsFlow()


class LocaOptionsFlow(OptionsFlow):
    """Pozwala zmienić częstotliwość odpytywania."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Zapisz nowy interwał aktualizacji."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPDATE_HOURS, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=24, step=1, mode=NumberSelectorMode.BOX
                        )
                    )
                }
            ),
        )
