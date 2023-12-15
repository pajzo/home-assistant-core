"""Sensor for myUplink."""
from collections.abc import Callable
from dataclasses import dataclass

from myuplink.models import DevicePoint

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import MyUplinkDataCoordinator
from .const import DOMAIN
from .coordinator import CoordinatorData
from .entity import MyUplinkEntity


@dataclass(kw_only=True)
class MyUplinkDeviceSensorEntityDescription(SensorEntityDescription):
    """Describes MyUplink device sensor entity."""

    value_fn: Callable[[CoordinatorData, str], StateType]


DEVICE_SENSORS: tuple[MyUplinkDeviceSensorEntityDescription, ...] = (
    MyUplinkDeviceSensorEntityDescription(
        key="firmware_current",
        name="Firmware Current",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, device_id: data.devices[device_id].firmwareCurrent,
    ),
    MyUplinkDeviceSensorEntityDescription(
        key="firmware_desired",
        name="Firmware Desired",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, device_id: data.devices[device_id].firmwareDesired,
    ),
    MyUplinkDeviceSensorEntityDescription(
        key="connection_state",
        name="Connection state",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, device_id: data.devices[device_id].connectionState,
    ),
)

DEVICE_POINT_DESCRIPTIONS = {
    "°C": SensorEntityDescription(
        key="data_point",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up myUplink sensor."""
    entities: list[SensorEntity] = []
    coordinator: MyUplinkDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Setup device sensors
    for device_id in coordinator.data.devices:
        for description in DEVICE_SENSORS:
            entities.append(
                MyUplinkDeviceSensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    entity_description=description,
                    unique_id_suffix=description.key,
                ),
            )

    # Setup device point sensors
    for device_id, point_data in coordinator.data.points.items():
        for point_id, device_point in point_data.items():
            entities.append(
                MyUplinkDevicePointSensor(
                    coordinator=coordinator,
                    device_id=device_id,
                    device_point=device_point,
                    entity_description=DEVICE_POINT_DESCRIPTIONS.get(
                        device_point.parameter_unit
                    ),
                    unique_id_suffix=point_id,
                )
            )

    async_add_entities(entities)


class MyUplinkDeviceSensor(MyUplinkEntity, SensorEntity):
    """Representation of a myUplink device sensor."""

    entity_description: MyUplinkDeviceSensorEntityDescription

    def __init__(
        self,
        coordinator: MyUplinkDataCoordinator,
        device_id: str,
        entity_description: MyUplinkDeviceSensorEntityDescription,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator=coordinator,
            device_id=device_id,
            unique_id_suffix=unique_id_suffix,
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType:
        """Sensor state value."""
        return self.entity_description.value_fn(self.coordinator.data, self.device_id)


class MyUplinkDevicePointSensor(MyUplinkEntity, SensorEntity):
    """Representation of a myUplink device point sensor."""

    def __init__(
        self,
        coordinator: MyUplinkDataCoordinator,
        device_id: str,
        device_point: DevicePoint,
        entity_description: SensorEntityDescription | None,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator=coordinator,
            device_id=device_id,
            unique_id_suffix=unique_id_suffix,
        )

        # Internal properties
        self.point_id = device_point.parameter_id

        if entity_description is not None:
            self.entity_description = entity_description
        else:
            self._attr_native_unit_of_measurement = device_point.parameter_unit

    @property
    def native_value(self) -> StateType:
        """Sensor state value."""
        device_point = self.coordinator.data.points[self.device_id][self.point_id]
        return device_point.value  # type: ignore[no-any-return]
