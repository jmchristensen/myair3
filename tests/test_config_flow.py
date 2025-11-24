"""Tests for MyAir3 config flow."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_setup_entry():
    """Mock setup entry."""
    with patch(
        "custom_components.myair3.async_setup_entry",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock:
        yield mock


async def test_user_flow_success(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test successful user config flow."""
    with patch(
        "custom_components.myair3.config_flow.validate_host",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            "myair3", context={"source": "user"}
        )
        assert result.get("type") == "form"
        assert result.get("step_id") == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.168.1.100"}
        )
        assert result.get("type") == "create_entry"
        assert result.get("title") == "MyAir3 (192.168.1.100)"


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test user config flow when connection fails."""
    with patch(
        "custom_components.myair3.config_flow.validate_host",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_init(
            "myair3", context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.168.1.100"}
        )
        assert result.get("type") == "form"
        errors = result.get("errors") or {}
        assert errors.get("base") == "cannot_connect"


async def test_user_flow_duplicate_entry(hass: HomeAssistant) -> None:
    """Test duplicate config entry."""
    with patch(
        "custom_components.myair3.config_flow.validate_host",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            "myair3", context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.168.1.100"}
        )
        assert result.get("type") == "create_entry"

        # Try to add the same host again
        result = await hass.config_entries.flow.async_init(
            "myair3", context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.168.1.100"}
        )
        assert result.get("type") == "abort"
        assert result.get("reason") == "already_configured"
