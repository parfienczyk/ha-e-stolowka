"""Encje sensorów z jadłospisem."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MenuDay
from .const import (
    ATTR_DATE,
    ATTR_DAYS,
    ATTR_DIET,
    ATTR_DISHES,
    ATTR_MENU,
    ATTR_WEEK_END,
    ATTR_WEEK_START,
    CONF_BASE_URL,
    DOMAIN,
)
from .coordinator import LocaConfigEntry, LocaCoordinator

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class LocaSensorDescription(SensorEntityDescription):
    """Opis sensora wraz z regułą wyliczania stanu."""

    value: Callable[[LocaCoordinator], str | int | None]
    attributes: Callable[[LocaCoordinator], dict[str, Any]]


def _day_summary(coordinator: LocaCoordinator, offset: int) -> str | None:
    """Stan sensora dziennego: dania w jednej linii."""
    day = coordinator.day(offset)
    return day.summary if day and day.dishes else None


def _day_attributes(day: MenuDay | None) -> dict[str, Any]:
    """Atrybuty sensora dziennego."""
    if day is None:
        return {ATTR_DATE: None, ATTR_DISHES: [], ATTR_DIET: [], ATTR_MENU: ""}
    return {
        ATTR_DATE: day.day.isoformat(),
        ATTR_DISHES: day.dishes,
        ATTR_DIET: day.diet,
        ATTR_MENU: day.text,
    }


def _week_attributes(coordinator: LocaCoordinator) -> dict[str, Any]:
    """Atrybuty sensora tygodniowego: cały pobrany jadłospis."""
    data = coordinator.data or {}
    days = sorted(data)
    return {
        ATTR_WEEK_START: days[0].isoformat() if days else None,
        ATTR_WEEK_END: days[-1].isoformat() if days else None,
        ATTR_DAYS: {
            day.isoformat(): {
                ATTR_DISHES: data[day].dishes,
                ATTR_DIET: data[day].diet,
                ATTR_MENU: data[day].text,
            }
            for day in days
        },
    }


SENSORS: tuple[LocaSensorDescription, ...] = (
    LocaSensorDescription(
        key="today",
        translation_key="today",
        icon="mdi:food-fork-drink",
        value=lambda c: _day_summary(c, 0),
        attributes=lambda c: _day_attributes(c.day(0)),
    ),
    LocaSensorDescription(
        key="tomorrow",
        translation_key="tomorrow",
        icon="mdi:food-outline",
        value=lambda c: _day_summary(c, 1),
        attributes=lambda c: _day_attributes(c.day(1)),
    ),
    LocaSensorDescription(
        key="week",
        translation_key="week",
        icon="mdi:calendar-week",
        native_unit_of_measurement="dni",
        value=lambda c: len(c.data) if c.data else 0,
        attributes=_week_attributes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LocaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Dodaj sensory jadłospisu."""
    coordinator = entry.runtime_data
    async_add_entities(
        LocaSensor(coordinator, entry, description) for description in SENSORS
    )


class LocaSensor(CoordinatorEntity[LocaCoordinator], SensorEntity):
    """Sensor pokazujący jadłospis."""

    _attr_has_entity_name = True
    entity_description: LocaSensorDescription

    def __init__(
        self,
        coordinator: LocaCoordinator,
        entry: LocaConfigEntry,
        description: LocaSensorDescription,
    ) -> None:
        """Przypisz sensor do urządzenia reprezentującego stołówkę."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="loca.pl",
            name=f"e-Stołówka {entry.title}",
            configuration_url=entry.data[CONF_BASE_URL],
        )

    async def async_added_to_hass(self) -> None:
        """Przelicz stan o północy, nie czekając na kolejne odpytanie.

        „Dziś” i „jutro” zależą od bieżącej daty, a nie od nowych danych —
        bez tego po północy encje pokazywałyby wczorajszy jadłospis aż do
        następnego pobrania, czyli domyślnie nawet kilka godzin.
        """
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._async_day_changed, hour=0, minute=0, second=0
            )
        )

    @callback
    def _async_day_changed(self, now: datetime) -> None:
        """Zapisz stan po zmianie dnia."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | int | None:
        """Stan sensora."""
        return self.entity_description.value(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Pełny jadłospis w atrybutach — stan nie pomieści długich dań."""
        return self.entity_description.attributes(self.coordinator)
