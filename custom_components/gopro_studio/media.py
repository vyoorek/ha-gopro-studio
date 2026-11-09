"""Model plików na karcie kamery (lista z /gopro/media/list)."""
from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field

VIDEO_EXT = (".MP4", ".360")
MIME = {".MP4": "video/mp4", ".360": "video/mp4", ".JPG": "image/jpeg", ".GPR": "image/x-adobe-dng",
        ".LRV": "video/mp4", ".THM": "image/jpeg", ".WAV": "audio/wav"}


def cam_time(epoch) -> dt.datetime:
    """Kamera zapisuje czas lokalny jako epoch - interpretujemy go bez strefy."""
    try:
        return dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(epoch))
    except (TypeError, ValueError):
        return dt.datetime(1970, 1, 1)


@dataclass
class MediaItem:
    folder: str
    name: str
    size: int
    created: dt.datetime
    kind: str               # video | photo | group
    raw: bool = False
    lrv_size: int = 0
    group_type: str = ""
    members: list[str] = field(default_factory=list)

    @property
    def path(self) -> str:
        return f"{self.folder}/{self.name}"

    @property
    def ext(self) -> str:
        return os.path.splitext(self.name)[1].upper()

    @property
    def mime(self) -> str:
        return MIME.get(self.ext, "application/octet-stream")

    def files(self, include_raw: bool = True, include_lrv: bool = False) -> list[str]:
        """Nazwy plików do pobrania (seria = wszystkie zdjęcia, RAW = dodatkowy .GPR)."""
        names = self.members if self.kind == "group" else [self.name]
        out = []
        for n in names:
            out.append(n)
            if include_raw and self.raw and n.upper().endswith(".JPG"):
                out.append(n[:-4] + ".GPR")
        if include_lrv and self.kind == "video" and self.lrv_size:
            base = os.path.splitext(self.name)[0]
            out.append(base[0] + "L" + base[2:] + ".LRV")
        return out


def parse_media_list(data: dict) -> list[MediaItem]:
    items: list[MediaItem] = []
    for d in data.get("media", []):
        folder = d.get("d", "")
        for f in d.get("fs", []):
            n = f.get("n", "")
            ext = os.path.splitext(n)[1].upper()
            item = MediaItem(folder=folder, name=n, size=int(f.get("s", 0) or 0),
                             created=cam_time(f.get("cre", 0)),
                             kind="video" if ext in VIDEO_EXT else "photo",
                             raw=str(f.get("raw", "0")) == "1",
                             lrv_size=int(f.get("glrv", 0) or 0))
            if "b" in f and "l" in f:
                item.kind = "group"
                item.group_type = f.get("t", "")
                missing = {int(x) for x in f.get("m", []) or []}
                try:
                    first, last = int(f["b"]), int(f["l"])
                    item.members = [f"{n[:4]}{i:04d}{ext}" for i in range(first, last + 1) if i not in missing]
                except ValueError:
                    item.members = [n]
            items.append(item)
    items.sort(key=lambda i: (i.created, i.name), reverse=True)
    return items
