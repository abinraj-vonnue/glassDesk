"""Plain readers for live system data. No GTK here."""

import os
import re
import time

_IGNORED_NET_PREFIXES = ("docker", "veth", "br-", "virbr", "tun", "tap")


def cpu_model():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    name = line.split(":", 1)[1].strip()
                    break
            else:
                return "Processor"
    except OSError:
        return "Processor"
    name = re.sub(r"\((R|TM)\)", "", name)
    name = re.sub(r"\s+@.*$", "", name)
    name = re.sub(r"\s+CPU\b", "", name)
    name = re.sub(r"^\d+(st|nd|rd|th) Gen\s+", "", name)
    return " ".join(name.split()) or "Processor"


class CpuSampler:
    """Overall CPU usage (%) between successive calls, from /proc/stat."""

    def __init__(self):
        self._prev = self._read()

    @staticmethod
    def _read():
        try:
            with open("/proc/stat") as f:
                values = [int(x) for x in f.readline().split()[1:]]
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            return sum(values[:8]), idle
        except (OSError, ValueError, IndexError):
            return None

    def percent(self):
        cur = self._read()
        prev, self._prev = self._prev, cur
        if cur is None or prev is None:
            return 0.0
        total = cur[0] - prev[0]
        idle = cur[1] - prev[1]
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, 100.0 * (total - idle) / total))


def memory():
    """Return (used_bytes, total_bytes) or None."""
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                key, value = line.split(":", 1)
                if key in ("MemTotal", "MemAvailable"):
                    info[key] = int(value.split()[0]) * 1024
                if len(info) == 2:
                    break
    except (OSError, ValueError):
        return None
    if len(info) < 2 or info["MemTotal"] <= 0:
        return None
    return info["MemTotal"] - info["MemAvailable"], info["MemTotal"]


class NetSampler:
    """Download/upload rates in bytes/s from /proc/net/dev."""

    def __init__(self):
        self._prev = self._read()
        self._time = time.monotonic()

    @staticmethod
    def _read():
        try:
            with open("/proc/net/dev") as f:
                lines = f.readlines()[2:]
        except OSError:
            return None
        rx = tx = 0
        for line in lines:
            name, data = line.split(":", 1)
            name = name.strip()
            if name == "lo" or name.startswith(_IGNORED_NET_PREFIXES):
                continue
            fields = data.split()
            rx += int(fields[0])
            tx += int(fields[8])
        return rx, tx

    def rates(self):
        now = time.monotonic()
        cur = self._read()
        if cur is None or self._prev is None:
            self._prev, self._time = cur, now
            return 0.0, 0.0
        dt = now - self._time
        if dt < 0.05:
            return 0.0, 0.0
        down = max(0.0, (cur[0] - self._prev[0]) / dt)
        up = max(0.0, (cur[1] - self._prev[1]) / dt)
        self._prev, self._time = cur, now
        return down, up


def disk_usage(path):
    """Return (used_bytes, total_bytes) like `df`, or None."""
    try:
        st = os.statvfs(path)
    except OSError:
        return None
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    total = used + st.f_bavail * st.f_frsize
    if total <= 0:
        return None
    return used, total


def has_separate_home():
    return os.path.ismount("/home")


def fmt_size(num_bytes):
    gb = num_bytes / 2**30
    if gb >= 1024:
        return f"{gb / 1024:.1f} TB"
    if gb >= 100:
        return f"{gb:.0f} GB"
    return f"{gb:.1f} GB"


def fmt_rate(bytes_per_s):
    if bytes_per_s >= 1024**2:
        return f"{bytes_per_s / 1024**2:.1f} MB/s"
    if bytes_per_s >= 1024:
        return f"{bytes_per_s / 1024:.0f} KB/s"
    return f"{bytes_per_s:.0f} B/s"
