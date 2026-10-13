import sysinfo

from .base import ICE, Sparkline, Tile, every, make_label

ICONS = ("cpu-symbolic", "computer-symbolic", "utilities-system-monitor-symbolic")


class CpuTile(Tile):
    def __init__(self, width=None):
        super().__init__("CPU", ICONS, width)

        self.value = make_label("0%", "tile-value")
        self.add_header_end(self.value)

        self.pack_start(make_label(sysinfo.cpu_model(), "tile-meta"), False, False, 0)
        self.graph = Sparkline(ICE, fixed_max=100, height=48)
        self.pack_start(self.graph, False, False, 0)

        self._sampler = sysinfo.CpuSampler()
        every(1, self.update)

    def update(self):
        percent = self._sampler.percent()
        self.value.set_text(f"{percent:.0f}%")
        self.graph.push(percent)
