from __future__ import annotations

import argparse
import csv
import ctypes
import json
import math
import os
import sys
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


TRANSPARENT = "#010101"
CUTE_FONT = "SKMZKAT"
FALLBACK_FONT = "Arial Rounded MT Bold"
FONT_ASSET = Path("assets") / "ShiKeMengZhiKeAiTi" / "ShiKeMengZhiKeAiTi-2.ttf"
DEFAULT_CONFIG = {
    "keys": ["D", "F", "J", "K"],
    "idle_reset_seconds": 0.67,
    "interval_count": 4,
    "total_kps_window_seconds": 1.0,
    "smoothing_seconds_to_90_percent": 0.2,
    "timing_log_enabled": True,
    "size": 420,
    "position": {"x": 800, "y": 450},
    "opacity": 0.96,
    "refresh_hz": 120,
    "segments": [
        {"from_bpm": 0, "to_bpm": 75, "color": "#07542F"},
        {"from_bpm": 75, "to_bpm": 150, "color": "#25A244"},
        {"from_bpm": 150, "to_bpm": 180, "color": "#F2C94C"},
        {"from_bpm": 180, "to_bpm": 195, "color": "#E53935"},
        {"from_bpm": 195, "to_bpm": 240, "color": "#8B1018"},
    ],
}


NAMED_KEYS = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "ALT": 0x12,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "ESC": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
}
NAMED_KEYS.update({f"F{i}": 0x6F + i for i in range(1, 13)})


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    color: str


@dataclass(frozen=True)
class Config:
    keys: tuple[str, ...]
    idle_reset_seconds: float
    interval_count: int
    total_kps_window_seconds: float
    smoothing_seconds_to_90_percent: float
    timing_log_enabled: bool
    size: int
    x: str | int
    y: int
    opacity: float
    refresh_hz: int
    segments: tuple[Segment, ...]

    @property
    def max_bpm(self) -> float:
        return self.segments[-1].end


def normalize_key(name: object) -> str:
    value = str(name).strip().upper()
    aliases = {"CONTROL": "CTRL", "RETURN": "ENTER", "ESCAPE": "ESC", "PGUP": "PAGEUP", "PGDN": "PAGEDOWN"}
    return aliases.get(value, value)


def virtual_key(name: str) -> int:
    name = normalize_key(name)
    if name in NAMED_KEYS:
        return NAMED_KEYS[name]
    if len(name) == 1 and name.isascii() and name.isalnum():
        return ord(name)
    raise ValueError(f"不支持的按键名称: {name}")


def _is_color(value: object) -> bool:
    text = str(value)
    if len(text) != 7 or not text.startswith("#"):
        return False
    try:
        int(text[1:], 16)
        return True
    except ValueError:
        return False


def parse_config(data: dict) -> Config:
    keys = tuple(dict.fromkeys(normalize_key(k) for k in data.get("keys", [])))
    if not keys:
        raise ValueError("keys 至少需要一个按键")
    for key in keys:
        virtual_key(key)

    idle_reset_seconds = float(data.get("idle_reset_seconds", 0.67))
    interval_count = int(data.get("interval_count", 4))
    total_kps_window_seconds = float(data.get("total_kps_window_seconds", 1.0))
    smoothing_seconds = float(data.get("smoothing_seconds_to_90_percent", 0.2))
    timing_log_enabled = bool(data.get("timing_log_enabled", True))
    size = int(data.get("size", 420))
    opacity = float(data.get("opacity", 0.96))
    refresh_hz = int(data.get("refresh_hz", 120))
    if not 0.05 <= idle_reset_seconds <= 2:
        raise ValueError("idle_reset_seconds 必须在 0.05 到 2 之间")
    if not 1 <= interval_count <= 32:
        raise ValueError("interval_count 必须在 1 到 32 之间")
    if not 0.1 <= total_kps_window_seconds <= 10:
        raise ValueError("total_kps_window_seconds 必须在 0.1 到 10 之间")
    if not 0.01 <= smoothing_seconds <= 2:
        raise ValueError("smoothing_seconds_to_90_percent 必须在 0.01 到 2 之间")
    if not 220 <= size <= 1200:
        raise ValueError("size 必须在 220 到 1200 之间")
    if not 0.2 <= opacity <= 1.0:
        raise ValueError("opacity 必须在 0.2 到 1.0 之间")
    if not 30 <= refresh_hz <= 240:
        raise ValueError("refresh_hz 必须在 30 到 240 之间")

    position = data.get("position", {})
    x_raw = position.get("x", 800)
    x: str | int = "center" if str(x_raw).lower() == "center" else int(x_raw)
    y = int(position.get("y", 450))

    segments: list[Segment] = []
    expected_start = 0.0
    for raw in data.get("segments", []):
        start = float(raw["from_bpm"])
        end = float(raw["to_bpm"])
        color = str(raw["color"]).upper()
        if not math.isclose(start, expected_start) or end <= start:
            raise ValueError("segments 必须从 0 开始并且首尾连续递增")
        if not _is_color(color):
            raise ValueError(f"无效颜色: {color}")
        segments.append(Segment(start, end, color))
        expected_start = end
    if not segments:
        raise ValueError("segments 不能为空")
    return Config(keys, idle_reset_seconds, interval_count, total_kps_window_seconds, smoothing_seconds, timing_log_enabled, size, x, y, opacity, refresh_hz, tuple(segments))


def segment_for(bpm: float, segments: tuple[Segment, ...]) -> Segment:
    for segment in segments:
        if bpm < segment.end:
            return segment
    return segments[-1]


def mix_color(color: str, background: str = "#101217", amount: float = 0.28) -> str:
    source = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
    base = tuple(int(background[i : i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(round(b + (s - b) * amount) for s, b in zip(source, base))
    return "#" + "".join(f"{value:02X}" for value in mixed)


@dataclass(frozen=True)
class PressSample:
    key: str
    timestamp: float
    previous_interval: float | None
    latest_interval: float | None
    average_interval: float | None
    intervals: tuple[float, ...]
    target_kps: float
    reset_after_idle: bool


class TimingLogger:
    HEADER = (
        "wall_time",
        "monotonic_seconds",
        "event",
        "key",
        "hold_ms",
        "previous_interval_ms",
        "latest_interval_ms",
        "average_interval_ms",
        "target_kps",
        "target_bpm",
        "display_bpm",
        "note",
    )

    def __init__(self, path: Path):
        self.path = path
        is_new = not path.exists() or path.stat().st_size == 0
        self.handle = path.open("a", encoding="utf-8-sig", newline="")
        self.writer = csv.writer(self.handle)
        if is_new:
            self.writer.writerow(self.HEADER)
            self.handle.flush()

    @staticmethod
    def _milliseconds(value: float | None) -> str:
        return "" if value is None else f"{value * 1000:.3f}"

    def press(self, sample: PressSample, display_bpm: float) -> None:
        if sample.reset_after_idle:
            note = "idle_reset"
        elif sample.average_interval is None:
            note = "warming_up"
        else:
            intervals = "|".join(f"{value * 1000:.3f}" for value in sample.intervals)
            note = f"valid intervals_ms={intervals}"
        self._write(
            sample.timestamp,
            "DOWN",
            sample.key,
            "",
            self._milliseconds(sample.previous_interval),
            self._milliseconds(sample.latest_interval),
            self._milliseconds(sample.average_interval),
            f"{sample.target_kps:.4f}",
            f"{sample.target_kps * 15:.2f}",
            f"{display_bpm:.2f}",
            note,
        )

    def release(self, key: str, timestamp: float, held_seconds: float | None, display_bpm: float) -> None:
        self._write(
            timestamp,
            "UP",
            key,
            self._milliseconds(held_seconds),
            "",
            "",
            "",
            "",
            "",
            f"{display_bpm:.2f}",
            "",
        )

    def _write(self, timestamp: float, event: str, key: str, *values: str) -> None:
        self.writer.writerow(
            [datetime.now().isoformat(timespec="milliseconds"), f"{timestamp:.6f}", event, key, *values]
        )
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


class IntervalKps:
    def __init__(self, keys: Iterable[str], idle_reset_seconds: float, interval_count: int = 2):
        self.idle_reset_seconds = idle_reset_seconds
        self.interval_count = interval_count
        self.events = {key: deque(maxlen=interval_count + 1) for key in keys}

    def reconfigure(self, keys: Iterable[str], idle_reset_seconds: float, interval_count: int) -> None:
        self.idle_reset_seconds = idle_reset_seconds
        self.interval_count = interval_count
        max_events = interval_count + 1
        self.events = {
            key: deque(list(self.events.get(key, ()))[-max_events:], maxlen=max_events)
            for key in keys
        }

    def press(self, key: str, timestamp: float) -> PressSample:
        events = self.events[key]
        reset_after_idle = bool(events and timestamp - events[-1] > self.idle_reset_seconds)
        if reset_after_idle:
            events.clear()
        events.append(timestamp)
        intervals = tuple(events[index] - events[index - 1] for index in range(1, len(events)))
        previous_interval = intervals[-2] if len(intervals) >= 2 else None
        latest_interval = events[-1] - events[-2] if len(events) >= 2 else None
        average_interval = (
            sum(intervals) / len(intervals)
            if len(intervals) == self.interval_count
            else None
        )
        target_kps = 1 / average_interval if average_interval and average_interval > 0 else 0.0
        return PressSample(
            key,
            timestamp,
            previous_interval,
            latest_interval,
            average_interval,
            intervals,
            target_kps,
            reset_after_idle,
        )

    def rates(self, now: float) -> dict[str, float]:
        rates: dict[str, float] = {}
        for key, events in self.events.items():
            if not events or now - events[-1] > self.idle_reset_seconds:
                events.clear()
                rates[key] = 0.0
                continue
            if len(events) < self.interval_count + 1:
                rates[key] = 0.0
                continue
            average_interval = (events[-1] - events[0]) / self.interval_count
            rates[key] = 1 / average_interval if average_interval > 0 else 0.0
        return rates


class RollingTotalKps:
    def __init__(self, window_seconds: float):
        self.window_seconds = window_seconds
        self.events: deque[float] = deque()

    def reconfigure(self, window_seconds: float, clear: bool = False) -> None:
        self.window_seconds = window_seconds
        if clear:
            self.events.clear()

    def press(self, timestamp: float) -> None:
        self.events.append(timestamp)

    def rate(self, now: float) -> float:
        cutoff = now - self.window_seconds
        while self.events and self.events[0] < cutoff:
            self.events.popleft()
        return len(self.events) / self.window_seconds


def exponential_approach(current: float, target: float, elapsed: float, seconds_to_90_percent: float) -> float:
    if elapsed <= 0:
        return current
    decay = math.exp(-math.log(10) * elapsed / seconds_to_90_percent)
    return target + (current - target) * decay


class Overlay:
    def __init__(self, config_path: Path, demo_bpm: float | None = None):
        self.config_path = config_path
        self.demo_bpm = demo_bpm
        self.config = self._load_config()
        self.config_mtime = self.config_path.stat().st_mtime_ns
        self.stats = IntervalKps(self.config.keys, self.config.idle_reset_seconds, self.config.interval_count)
        self.total_stats = RollingTotalKps(self.config.total_kps_window_seconds)
        self.display_bpm = 0.0
        self.display_total_kps = 0.0
        self.last_frame_time = time.perf_counter()
        self.vks: dict[str, int] = {}
        self.held: dict[str, bool] = {}
        self.down_times: dict[str, float] = {}
        self.last_reload_check = 0.0
        self.timing_logger = TimingLogger(self.config_path.with_name("key-timing.csv")) if self.config.timing_log_enabled else None

        self.font_family = CUTE_FONT if load_private_font(resource_path(FONT_ASSET)) else FALLBACK_FONT
        self.root = tk.Tk()
        self.root.title("KPS Overlay")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config.opacity)
        self.root.configure(bg=TRANSPARENT)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT)
        self.canvas = tk.Canvas(self.root, bg=TRANSPARENT, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._apply_config(initial=True)
        self.root.after(30, self._make_click_through)

    def _load_config(self) -> Config:
        with self.config_path.open("r", encoding="utf-8") as handle:
            return parse_config(json.load(handle))

    def _geometry(self) -> tuple[int, int]:
        width = self.config.size
        height = round(self.config.size * 0.72)
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        x = (screen_width - width) // 2 if self.config.x == "center" else int(self.config.x)
        return width, height, x, self.config.y

    def _apply_config(self, initial: bool = False) -> None:
        width, height, x, y = self._geometry()
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.canvas.configure(width=width, height=height)
        self.root.attributes("-alpha", self.config.opacity)
        self.stats.reconfigure(self.config.keys, self.config.idle_reset_seconds, self.config.interval_count)
        self.total_stats.reconfigure(self.config.total_kps_window_seconds, clear=not initial)
        self.vks = {key: virtual_key(key) for key in self.config.keys}
        self.held = {key: False for key in self.config.keys}
        self.down_times = {}
        if self.config.timing_log_enabled and self.timing_logger is None:
            self.timing_logger = TimingLogger(self.config_path.with_name("key-timing.csv"))
        elif not self.config.timing_log_enabled and self.timing_logger is not None:
            self.timing_logger.close()
            self.timing_logger = None
        if not initial:
            self._make_click_through()

    def _make_click_through(self) -> None:
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        get_window_long = ctypes.windll.user32.GetWindowLongW
        set_window_long = ctypes.windll.user32.SetWindowLongW
        style = get_window_long(hwnd, -20)
        set_window_long(hwnd, -20, style | 0x00000020 | 0x00000080 | 0x08000000)

    def _poll_keys(self, now: float) -> None:
        user32 = ctypes.windll.user32
        states: dict[str, bool] = {}
        for key, vk in self.vks.items():
            down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            states[key] = down
            if key in self.stats.events and down and not self.held.get(key, False):
                self.down_times[key] = now
                sample = self.stats.press(key, now)
                self.total_stats.press(now)
                if self.timing_logger:
                    self.timing_logger.press(sample, self.display_bpm)
            elif key in self.stats.events and not down and self.held.get(key, False):
                pressed_at = self.down_times.pop(key, None)
                held_seconds = now - pressed_at if pressed_at is not None else None
                if self.timing_logger:
                    self.timing_logger.release(key, now, held_seconds, self.display_bpm)
        self.held = states

    def _close(self) -> None:
        if self.timing_logger:
            self.timing_logger.close()
            self.timing_logger = None
        self.root.destroy()
    def _reload_if_changed(self, now: float) -> None:
        if now - self.last_reload_check < 1:
            return
        self.last_reload_check = now
        try:
            mtime = self.config_path.stat().st_mtime_ns
            if mtime == self.config_mtime:
                return
            new_config = self._load_config()
            self.config = new_config
            self.config_mtime = mtime
            self._apply_config()
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self._log(f"配置重载失败: {exc}")

    def _point(self, angle: float, radius: float, cx: float, cy: float) -> tuple[float, float]:
        radians = math.radians(angle)
        return cx + radius * math.cos(radians), cy + radius * math.sin(radians)

    def _bpm_angle(self, bpm: float) -> float:
        return 150 + 240 * max(0, min(bpm / self.config.max_bpm, 1))

    def _arc(self, start_bpm: float, end_bpm: float, radius: float, cx: float, cy: float, color: str, width: int) -> None:
        start_angle = self._bpm_angle(start_bpm)
        end_angle = self._bpm_angle(end_bpm)
        steps = max(3, round((end_angle - start_angle) / 0.75))
        points: list[float] = []
        for index in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * index / steps
            points.extend(self._point(angle, radius, cx, cy))
        self.canvas.create_line(
            *points,
            fill=color,
            width=width,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
            smooth=True,
            splinesteps=36,
        )

    def _draw(self, bpm: float, total_kps: float, fastest_key: str) -> None:
        self.canvas.delete("all")
        size = self.config.size
        cx, cy = size / 2, size * 0.405
        radius = size * 0.31
        scale = size / 420
        current = segment_for(bpm, self.config.segments)
        inner_radius = radius - 7 * scale

        self.canvas.create_oval(
            cx - inner_radius,
            cy - inner_radius,
            cx + inner_radius,
            cy + inner_radius,
            fill=mix_color(current.color),
            outline=mix_color(current.color, amount=0.72),
            width=max(1, round(scale)),
        )
        self._arc(0, self.config.max_bpm, radius, cx, cy, "#34373D", max(7, round(10 * scale)))
        for segment in self.config.segments:
            self._arc(segment.start, segment.end, radius, cx, cy, segment.color, max(5, round(8 * scale)))

        boundaries = [segment.start for segment in self.config.segments] + [self.config.max_bpm]
        for boundary in boundaries:
            angle = self._bpm_angle(boundary)
            inner = self._point(angle, radius - 17 * scale, cx, cy)
            outer = self._point(angle, radius - 4 * scale, cx, cy)
            label = self._point(angle, radius - 31 * scale, cx, cy)
            self.canvas.create_line(*inner, *outer, fill="#F3F4F6", width=max(1, round(scale)), capstyle=tk.ROUND)
            self.canvas.create_text(
                *label,
                text=f"{boundary:g}",
                fill="#E6E7EA",
                font=(self.font_family, max(7, round(9 * scale)), "bold"),
            )

        pointer_angle = self._bpm_angle(bpm)
        pointer_tip = self._point(pointer_angle, radius - 17 * scale, cx, cy)
        pointer_back = self._point(pointer_angle + 180, 12 * scale, cx, cy)
        self.canvas.create_line(*pointer_back, *pointer_tip, fill="#FFFFFF", width=max(3, round(4 * scale)), capstyle=tk.ROUND)
        self.canvas.create_oval(cx - 5 * scale, cy - 5 * scale, cx + 5 * scale, cy + 5 * scale, fill=current.color, outline="#FFFFFF", width=max(1, round(scale)))

        bpm_text = f"{bpm:.0f}"
        key_text = fastest_key if fastest_key else "-"
        self.canvas.create_text(
            cx - 7 * scale,
            cy - 42 * scale,
            text=bpm_text,
            fill="#FFFFFF",
            font=(self.font_family, max(18, round(35 * scale)), "bold"),
        )
        self.canvas.create_text(
            cx + 44 * scale,
            cy - 26 * scale,
            text="BPM",
            anchor=tk.NW,
            fill="#E6E7EA",
            font=(self.font_family, max(7, round(9 * scale)), "bold"),
        )
        self.canvas.create_text(
            cx,
            cy - 8 * scale,
            text=key_text,
            fill="#D8DAE0",
            font=(self.font_family, max(8, round(11 * scale)), "bold"),
        )
        self.canvas.create_text(
            cx,
            cy + 45 * scale,
            text=f"{total_kps:.0f}  KPS",
            fill="#FFFFFF",
            font=(self.font_family, max(12, round(18 * scale)), "bold"),
        )

    def _tick(self) -> None:
        now = time.perf_counter()
        elapsed = min(max(now - self.last_frame_time, 0), 0.25)
        self.last_frame_time = now
        self._reload_if_changed(now)
        if self.demo_bpm is None:
            self._poll_keys(now)
            rates = self.stats.rates(now)
            fastest_key = max(rates, key=rates.get) if rates and max(rates.values()) > 0 else ""
            fastest_kps = rates.get(fastest_key, 0)
            target_bpm = fastest_kps * 15
            target_total_kps = self.total_stats.rate(now)
        else:
            target_bpm = self.demo_bpm
            target_total_kps = target_bpm / 15 * len(self.config.keys)
            fastest_key = self.config.keys[0]
        smoothing = self.config.smoothing_seconds_to_90_percent
        self.display_bpm = exponential_approach(self.display_bpm, target_bpm, elapsed, smoothing)
        self.display_total_kps = target_total_kps
        self._draw(self.display_bpm, self.display_total_kps, fastest_key)
        self.root.after(max(4, round(1000 / self.config.refresh_hz)), self._tick)

    def _log(self, message: str) -> None:
        try:
            with self.config_path.with_name("kps-overlay.log").open("a", encoding="utf-8") as handle:
                handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
        except OSError:
            pass

    def run(self) -> None:
        self._tick()
        self.root.mainloop()


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(relative_path: Path) -> Path:
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_dir / relative_path


def load_private_font(path: Path) -> bool:
    if not path.is_file():
        return False
    added = ctypes.windll.gdi32.AddFontResourceExW(str(path), 0x10, 0)
    # FR_PRIVATE fonts are visible only to this process. Broadcasting here can
    # block startup indefinitely while an unrelated window is unresponsive.
    return bool(added)


def ensure_config(path: Path) -> None:
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows 音游 KPS/BPM 置顶覆盖层")
    parser.add_argument("--config", type=Path, default=app_directory() / "config.json")
    parser.add_argument("--demo-bpm", type=float, help="使用固定 BPM 预览界面")
    args = parser.parse_args()
    config_path = args.config.resolve()
    ensure_config(config_path)
    try:
        Overlay(config_path, args.demo_bpm).run()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        ctypes.windll.user32.MessageBoxW(None, f"无法启动 KPS Overlay:\n{exc}", "KPS Overlay", 0x10)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
