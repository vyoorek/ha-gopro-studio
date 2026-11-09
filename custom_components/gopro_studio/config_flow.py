"""Konfiguracja z interfejsu HA: dodanie kamery, ponowne logowanie, zmiana adresu, opcje."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GoProApi, GoProAuthError, GoProError
from .const import (CONF_AUTO_PHOTO, CONF_AUTO_TIMELAPSE, CONF_AUTO_VIDEO, CONF_DOWNLOAD_DIR, CONF_HTTPS, CONF_KEEP_ALIVE, CONF_PREVIEW, CONF_PREVIEW_PORT,
                    CONF_SCAN_INTERVAL, DEFAULT_KEEP_ALIVE, DEFAULT_PREVIEW, DEFAULT_PREVIEW_PORT,
                    DEFAULT_SCAN_INTERVAL, DEFAULT_USERNAME, DOMAIN)


def _schema(d: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_HOST, default=d.get(CONF_HOST, "")): str,
        vol.Optional(CONF_USERNAME, default=d.get(CONF_USERNAME, DEFAULT_USERNAME)): str,
        vol.Optional(CONF_PASSWORD, default=d.get(CONF_PASSWORD, "")): str,
        vol.Optional(CONF_HTTPS, default=d.get(CONF_HTTPS, True)): bool,
    })


class GoProStudioConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 2

    async def _validate(self, data: dict[str, Any]) -> tuple[dict | None, str | None]:
        api = GoProApi(async_get_clientsession(self.hass, verify_ssl=False), data[CONF_HOST],
                       data.get(CONF_USERNAME, ""), data.get(CONF_PASSWORD, ""), data.get(CONF_HTTPS, True))
        try:
            info = await api.info()
        except GoProAuthError:
            return None, "invalid_auth"
        except GoProError:
            return None, "cannot_connect"
        if not info.get("serial_number"):
            return None, "not_gopro"
        return info, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            info, err = await self._validate(user_input)
            if err:
                errors["base"] = err
            else:
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(title=f"{info.get('model_name', 'GoPro')} ({info['serial_number'][-4:]})",
                                               data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            info, err = await self._validate(user_input)
            if err:
                errors["base"] = err
            else:
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_mismatch(reason="wrong_camera")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(step_id="reconfigure", data_schema=_schema(user_input or dict(entry.data)),
                                    errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            info, err = await self._validate(data)
            if err:
                errors["base"] = err
            else:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(step_id="reauth_confirm", errors=errors, data_schema=vol.Schema({
            vol.Optional(CONF_USERNAME, default=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)): str,
            vol.Required(CONF_PASSWORD): str}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GoProStudioOptionsFlow()


class GoProStudioOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        o = self.config_entry.options
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=o.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)):
                vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
            vol.Optional(CONF_KEEP_ALIVE, default=o.get(CONF_KEEP_ALIVE, DEFAULT_KEEP_ALIVE)): bool,
            vol.Optional(CONF_PREVIEW, default=o.get(CONF_PREVIEW, DEFAULT_PREVIEW)): bool,
            vol.Optional(CONF_PREVIEW_PORT, default=o.get(CONF_PREVIEW_PORT, DEFAULT_PREVIEW_PORT)):
                vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
            vol.Optional(CONF_AUTO_PHOTO, default=o.get(CONF_AUTO_PHOTO, False)): bool,
            vol.Optional(CONF_AUTO_VIDEO, default=o.get(CONF_AUTO_VIDEO, False)): bool,
            vol.Optional(CONF_AUTO_TIMELAPSE, default=o.get(CONF_AUTO_TIMELAPSE, False)): bool,
            vol.Optional(CONF_DOWNLOAD_DIR, default=o.get(CONF_DOWNLOAD_DIR, "")): str,
        }))
