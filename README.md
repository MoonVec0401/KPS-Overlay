# KPS Overlay

适用于 Windows 音游的透明按键速度悬浮窗，实时显示 BPM 和总 KPS。窗口置顶、鼠标穿透，适合游戏和直播叠加。

## 使用方法

1. 在 GitHub 页面点击 **Code → Download ZIP**，下载并解压。
2. 打开 `dist` 文件夹，双击 `KPSOverlay.exe` 启动。
3. 双击 `ExitKPSOverlay.exe` 关闭悬浮窗。

默认统计 `D`、`F`、`J`、`K`。修改 `dist/config.json` 后，设置约一秒内自动生效。

## 自定义设置

| 配置项 | 作用 | 当前值 |
| --- | --- | --- |
| `keys` | 统计的按键 | `D`、`F`、`J`、`K` |
| `idle_reset_seconds` | 按键闲置后重置间隔的时间 | `0.67` 秒 |
| `interval_count` | 参与平均的最近按键间隔数 | `3` |
| `total_kps_window_seconds` | 总 KPS 的滚动统计窗口 | `1` 秒 |
| `smoothing_seconds_to_90_percent` | BPM 平滑过渡达到目标约 90% 的时间 | `0.2` 秒 |
| `timing_log_enabled` | 记录按键时间至 `key-timing.csv` | `true` |
| `size` | 悬浮窗宽度 | `420` |
| `position` | 窗口横纵坐标，横坐标可使用 `center` | `1100, 600` |
| `opacity` | 窗口不透明度 | `0.96` |
| `refresh_hz` | 界面刷新率 | `120` |
| `segments` | BPM 仪表的区间和颜色 | `0–240` BPM |

按键支持字母、数字、`F1`–`F12`、方向键、`SPACE`、`ENTER`、`CTRL`、`SHIFT`、`ALT` 等。

## 计算算法

- **BPM**：分别计算每个键最近 3 次按键间隔的平均值，单键 KPS = 1 ÷ 平均间隔（秒）；取最快键的 KPS × 15，得到按四分之一拍换算的 BPM。按键闲置 0.67 秒后，该键的间隔记录重置。
- **总 KPS**：统计最近 1 秒内所有配置按键的按下次数，除以窗口时长。
- **平滑显示**：BPM 数值和指针采用指数平滑，约 0.2 秒向目标值靠近 90%。上述时间和间隔数量均可在配置文件中调整。
