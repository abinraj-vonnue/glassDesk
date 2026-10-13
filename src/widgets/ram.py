import sysinfo

from .base import Tile, every, make_label, make_progress

ICONS = ("memory-symbolic", "drive-harddisk-solid-state-symbolic", "utilities-system-monitor-symbolic")


class RamTile(Tile):
    def __init__(self, width=None):
        super().__init__("RAM", ICONS, width)

        self.value = make_label("--", "tile-value")
        self.add_header_end(self.value)

        self.detail = make_label("", "tile-meta")
        self.bar = make_progress()
        self.pack_start(self.detail, False, False, 0)
        self.pack_start(self.bar, False, False, 0)

        every(2, self.update)

    def update(self):
        mem = sysinfo.memory()
        if mem is None:
            self.value.set_text("N/A")
            self.detail.set_text("Memory info unavailable")
            self.bar.set_fraction(0)
            return
        used, total = mem
        fraction = used / total
        self.value.set_text(f"{fraction * 100:.0f}%")
        self.detail.set_text(f"{sysinfo.fmt_size(used)} / {sysinfo.fmt_size(total)}")
        self.bar.set_fraction(fraction)
