# GoPro Studio for Home Assistant

Local control of GoPro cameras over the **Open GoPro HTTP API**: **Camera on the Home Network (COHN)**, camera Wi-Fi or USB. Includes **GoPro Labs** commands sent over Wi-Fi, without QR codes.

Tested with **HERO13 Black** running GoPro Labs firmware (H24.01.02.10.70).

## Features

| Platform | What you get |
|---|---|
| Sensor | battery, SD free space and capacity, remaining video time, remaining photos, video/photo count, recording time, camera state, active mode, SD status, Wi-Fi signal, last captured file, media count |
| Binary sensor | recording, busy, overheating, too cold, charging, SD problem, USB, preview active |
| Switch | **record** (start/stop), keep awake (keep-alive), turbo transfer, external control (locks the camera UI) |
| Button | shutter / take photo, stop, HiLight, sync time, locate (beep), sleep, refresh media, download latest file |
| Select | mode (video/photo/timelapse), **preset** (including custom presets), and **every camera setting** read from the camera schema. Options are filtered by the camera's own rules, so only valid values are shown. Main settings are enabled by default; the rest are in the entity registry. |
| Number | digital zoom |
| Text | **Labs command**: anything typed here is sent to the camera |
| Camera | image of the last capture; optional live preview (experimental) |
| Media browser | videos and photos on the SD card, with thumbnails and playback (streamed through HA, seeking supported) |

### Services

- `gopro_studio.labs_command`: send a GoPro Labs command, e.g. `$HIST=5$LEVL=5`, `*BITR=200`, `mV!20:00S!21:00E`
- `gopro_studio.set_setting`: set a setting by Open GoPro IDs (`setting_id`, `option_id`)
- `gopro_studio.load_preset`: load a preset by ID
- `gopro_studio.download_media`: download the latest, not-yet-downloaded or all files to HA (default `/media/gopro`), including RAW `.GPR` and optional `.LRV`. Can delete from the camera after download.
- `gopro_studio.delete_media`: delete one file or all files
- `gopro_studio.http_get`: send a raw GET request to the camera API (returns a response)

### Events

- `gopro_studio_download_finished`: `{camera, file, path}`
- `gopro_studio_labs_sent`: `{camera, command}`

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add this repository URL as type **Integration**.
2. Install **GoPro Studio** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → GoPro Studio**.
4. Enter the camera IP and the COHN credentials (username `gopro` plus a password). On a Labs camera, the command `$SHPS=20` shows the credentials and `$ADDR=15` shows the IP.

## Notes

- A sleeping camera leaves the network and can't be woken over Wi-Fi. Keep the **Keep awake** switch on while you use it. With Labs you can make the camera join the network automatically at boot: `*BOOT="!Lnet"!SAVEnet=!W`.
- Labs commands over Wi-Fi need GoPro Labs firmware for HERO13 **2.04.70 or newer**.
- Live preview: the camera sends MPEG-TS over UDP to the requesting host (HA, port 8554). It works with HA OS or host networking, and the UDP port must be reachable.

## Opis po polsku

Integracja steruje kamerą GoPro z Home Assistanta: nagrywanie, zdjęcia, tryby, presety i wszystkie ustawienia kamery. Udostępnia też sensory stanu, pobieranie mediów do HA (także RAW), przeglądarkę mediów z karty oraz wysyłanie komend **GoPro Labs przez Wi-Fi**, bez kodów QR. Konfiguracja odbywa się w interfejsie HA. Polskie tłumaczenie jest w zestawie.
