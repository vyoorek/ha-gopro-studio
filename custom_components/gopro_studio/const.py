"""Stałe integracji GoPro Studio."""
from __future__ import annotations

DOMAIN = "gopro_studio"
MANUFACTURER = "GoPro"

CONF_HTTPS = "https"
CONF_KEEP_ALIVE = "keep_alive"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PREVIEW = "preview"
CONF_DOWNLOAD_DIR = "download_dir"
CONF_PREVIEW_PORT = "preview_port"

DEFAULT_USERNAME = "gopro"
DEFAULT_SCAN_INTERVAL = 3
DEFAULT_KEEP_ALIVE = True
DEFAULT_PREVIEW = False
DEFAULT_PREVIEW_PORT = 8554

GROUP_VIDEO, GROUP_PHOTO, GROUP_TIMELAPSE = 1000, 1001, 1002
GROUP_OPTIONS = {GROUP_VIDEO: "video", GROUP_PHOTO: "photo", GROUP_TIMELAPSE: "timelapse"}
GROUP_KEYS = {"PRESET_GROUP_ID_VIDEO": GROUP_VIDEO, "PRESET_GROUP_ID_PHOTO": GROUP_PHOTO,
              "PRESET_GROUP_ID_TIMELAPSE": GROUP_TIMELAPSE}

# Statusy Open GoPro
ST_BATT_PRESENT = 1
ST_BATT_BARS = 2
ST_HOT = 6
ST_BUSY = 8
ST_ENCODING = 10
ST_VIDEO_SECS = 13
ST_PREVIEW = 32
ST_SD = 33
ST_PHOTOS_LEFT = 34
ST_VIDEO_LEFT = 35
ST_NUM_PHOTOS = 38
ST_NUM_VIDEOS = 39
ST_SPACE_KB = 54
ST_WIFI_BARS = 56
ST_BATT_PCT = 70
ST_ZOOM = 75
ST_ZOOM_AVAILABLE = 77
ST_COLD = 85
ST_GROUP = 96
ST_PRESET = 97
ST_TURBO = 113
ST_CONTROL = 114
ST_USB = 115
ST_SD_CAPACITY_KB = 117

SD_STATUS = {0: "ok", 1: "full", 2: "removed", 3: "format_error", 4: "busy", 8: "swapped", -1: "unknown"}

RESOLUTION_LABELS = {
    1: "4K 16:9", 4: "2.7K 16:9", 6: "2.7K 4:3", 7: "1440", 9: "1080 16:9", 12: "720",
    18: "4K 4:3", 24: "5K 16:9", 25: "5K 4:3", 26: "5.3K 8:7", 27: "5.3K 4:3", 28: "4K 8:7",
    35: "5.3K 21:9", 36: "4K 21:9", 37: "4K 1:1", 38: "900", 100: "5.3K 16:9",
    107: "5.3K 8:7", 108: "4K 8:7", 109: "4K 9:16", 110: "1080 9:16", 111: "2.7K 4:3",
    112: "4K 4:3", 113: "5.3K 4:3",
}

# Ustawienia włączone domyślnie (reszta jest dostępna, ale wyłączona w rejestrze encji)
PRIMARY_SETTINGS = {2, 3, 234, 121, 229, 135, 182, 183, 184, 125, 227, 230, 144, 115, 116, 117, 118, 145,
                    225, 59, 195, 167, 186, 187}
# Kategorie z gpControl, których nie zamieniamy w encje (to komendy, nie ustawienia)
SKIP_CATEGORIES = {"Delete", "About", "Manage Preset"}

EVENT_DOWNLOAD_FINISHED = f"{DOMAIN}_download_finished"
EVENT_LABS_SENT = f"{DOMAIN}_labs_sent"
