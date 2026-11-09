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
CONF_AUTO_PHOTO = "auto_download_photo"
CONF_AUTO_VIDEO = "auto_download_video"
CONF_AUTO_TIMELAPSE = "auto_download_timelapse"

DEFAULT_USERNAME = "gopro"
DEFAULT_SCAN_INTERVAL = 3
DEFAULT_KEEP_ALIVE = True
DEFAULT_PREVIEW = False
DEFAULT_PREVIEW_PORT = 8554

GROUP_VIDEO, GROUP_PHOTO, GROUP_TIMELAPSE = 1000, 1001, 1002
GROUP_OPTIONS = {GROUP_VIDEO: "video", GROUP_PHOTO: "photo", GROUP_TIMELAPSE: "timelapse"}
AUTO_DOWNLOAD_OPTION = {GROUP_VIDEO: CONF_AUTO_VIDEO, GROUP_PHOTO: CONF_AUTO_PHOTO,
                        GROUP_TIMELAPSE: CONF_AUTO_TIMELAPSE}
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
ST_FLATMODE = 89
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

# Status 89 (flatmode) -> sekcja; ustawienia przypisujemy do sekcji wg reguł kamery,
# które blokują dane ustawienie we wszystkich pozostałych trybach.
SECTION_VIDEO, SECTION_PHOTO, SECTION_TIMELAPSE, SECTION_GENERAL = "video", "photo", "timelapse", "general"
SECTIONS = (SECTION_VIDEO, SECTION_PHOTO, SECTION_TIMELAPSE, SECTION_GENERAL)
FLATMODE_SECTION = {
    12: SECTION_VIDEO, 15: SECTION_VIDEO, 32: SECTION_VIDEO, 35: SECTION_VIDEO,
    16: SECTION_PHOTO, 17: SECTION_PHOTO, 18: SECTION_PHOTO, 19: SECTION_PHOTO, 25: SECTION_PHOTO,
    27: SECTION_PHOTO,
    13: SECTION_TIMELAPSE, 20: SECTION_TIMELAPSE, 21: SECTION_TIMELAPSE, 22: SECTION_TIMELAPSE,
    23: SECTION_TIMELAPSE, 24: SECTION_TIMELAPSE, 26: SECTION_TIMELAPSE, 28: SECTION_TIMELAPSE,
    29: SECTION_TIMELAPSE, 30: SECTION_TIMELAPSE, 31: SECTION_TIMELAPSE,
}
# Ustawienia trybu prostego (Easy), których reguły nie wiążą z trybem
SECTION_OVERRIDES = {176: SECTION_VIDEO, 180: SECTION_VIDEO, 186: SECTION_VIDEO, 193: SECTION_VIDEO,
                     201: SECTION_VIDEO, 187: SECTION_TIMELAPSE}

# Ustawienia o tej samej nazwie w różnych trybach (121-123 to starsze odpowiedniki 229-231)
SETTING_NAME_OVERRIDES = {
    229: "Digital Lens", 230: "Digital Lens", 231: "Digital Lens",
    121: "Lens (legacy)", 122: "Lens (legacy)", 123: "Lens (legacy)",
    5: "Interval (Time Lapse Video)", 30: "Interval (Time Lapse Photo)", 32: "Interval (Night Lapse)",
    6: "Interval (Looping)", 19: "Shutter (Night Photo)", 31: "Shutter (Night Lapse)",
    176: "Speed (Easy)", 186: "Video Mode (Easy)", 193: "Framing (Easy)", 201: "Quality Control (Easy)",
    187: "Lapse Mode (Easy)",
    206: "Dashboard: Voice Commands", 207: "Dashboard: Screen Saver", 208: "Dashboard: Beeps",
    209: "Dashboard: Orientation", 210: "Dashboard: Front Display", 211: "Dashboard: Screen Lock",
    212: "Dashboard: LEDs",
}
# Kategorie, których ustawienia działają tylko w trakcie transmisji (poza nią kamera zwraca HTTP 500)
HIDDEN_CATEGORIES = {"Live Stream Settings"}
# Ustawienia, które mają sens tylko przy danej wartości innego ustawienia: {sid: (inne_sid, wartości)}
# 175 Controls: 0 = Easy, 1 = Pro; 205 Dashboard: 1 = On
SETTING_REQUIRES = {
    **{s: (175, (0,)) for s in (176, 186, 187, 193, 201)},
    **{s: (205, (1,)) for s in range(206, 213)},
}
# Ustawienia transmisji / kamery internetowej spoza tej kategorii
HIDDEN_SETTINGS = {41, 42, 44, 45, 47, 62, 64}

# Ustawienia włączone domyślnie (reszta jest dostępna, ale wyłączona w rejestrze encji)
PRIMARY_SETTINGS = {2, 3, 234, 229, 135, 182, 183, 184, 125, 227, 230, 144, 115, 116, 117, 118, 145,
                    225, 59, 195, 167, 186, 187}
# Kategorie z gpControl, których nie zamieniamy w encje (to komendy, nie ustawienia)
SKIP_CATEGORIES = {"Delete", "About", "Manage Preset"}

EVENT_DOWNLOAD_FINISHED = f"{DOMAIN}_download_finished"
EVENT_LABS_SENT = f"{DOMAIN}_labs_sent"
