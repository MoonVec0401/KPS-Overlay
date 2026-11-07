# KPS Overlay

适用于 Windows 音游的透明按键速度悬浮窗，实时展示 BPM 和总 KPS。

## 功能

- 全局统计指定按键，默认使用 `D`、`F`、`J`、`K`。
- 始终置顶、透明背景、鼠标穿透，适合游戏和直播叠加。
- 仪表盘显示最快按键的 BPM，数字同时显示全部按键的总 KPS。
- 支持自定义按键、位置、尺寸、颜色区间与刷新率，修改配置后自动重载。
- 内置时刻萌之可爱体，并支持按键时间记录。

## 快速开始

下载仓库中的 `dist` 文件夹，双击 `KPSOverlay.exe` 启动，双击 `ExitKPSOverlay.exe` 退出。编辑同目录的 `config.json` 可调整设置。

也可在 Windows 安装 Python 3.10 或更新版本后，通过 PowerShell 运行源码：

```powershell
python .\kps_overlay.py
```

退出悬浮窗：

```powershell
python .\exit_overlay.py
```

预览固定 BPM：

```powershell
python .\kps_overlay.py --demo-bpm 188
```

## 配置

编辑同目录下的 `config.json`，配置约一秒后自动生效。

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `keys` | 统计的按键 | `D`、`F`、`J`、`K` |
| `idle_reset_seconds` | 按键闲置后重置间隔的时间 | `0.67` 秒 |
| `interval_count` | 计算平均值的最近按键间隔数 | `4` |
| `total_kps_window_seconds` | 总 KPS 的滚动统计窗口 | `1` 秒 |
| `smoothing_seconds_to_90_percent` | BPM 平滑过渡达到目标约 90% 的时间 | `0.2` 秒 |
| `timing_log_enabled` | 记录按键时间至 `key-timing.csv` | `true` |
| `size` | 悬浮窗宽度 | `420` |
| `position` | 窗口横纵坐标；横坐标可使用 `center` | `800, 450` |
| `opacity` | 窗口不透明度 | `0.96` |
| `refresh_hz` | 界面刷新率 | `120` |
| `segments` | BPM 仪表区间及颜色 | `0–240` BPM |

按键支持字母、数字、`F1`–`F12`、方向键、`SPACE`、`ENTER`、`CTRL`、`SHIFT`、`ALT` 等。

每个键使用最近若干次按键间隔的平均值计算速度，最快键的每秒按键数乘以 15 得到四分之一拍 BPM；总 KPS 根据滚动窗口内全部配置键的按下次数计算。

## 构建 Windows 程序

```powershell
.\build.ps1
```

脚本安装 PyInstaller 并在 `dist` 目录生成 `KPSOverlay.exe`、`ExitKPSOverlay.exe` 和 `config.json`。双击主程序启动，双击退出工具关闭悬浮窗。

## 运行测试

```powershell
python -m unittest discover -s tests -v
```
