# Hardware map — gta4xlwifi (SM-P610, Exynos 9611)

Source: **live Gate 0 dumps from the actual tablet**, 2026-11-05
(Android 13, build P610XXS7FYD1), taken over ADB via the owner's
MSI laptop. Raw dumps stay local (they contain the device serial);
this file carries only hardware facts.

Legend: ✅ = read directly off the device. ◐ = node presence and
address confirmed on-device; property values (reg ranges, IRQ
numbers, clock rates) still to be confirmed against Samsung's
published kernel DTS for universal9611 — property *files* under
`/proc/device-tree` are not readable by the Android shell user,
and `/sys/firmware/fdt` is root-only (0400) on stock firmware.

## Identity / boot state ✅

| | |
| --- | --- |
| Model / codename | SM-P610 / `gta4xlwifi`, product `gta4xlwifixx` |
| SoC platform | `universal9611`, `ro.hardware = exynos9611` |
| Android build | 13 / TP1A.220624.014 / **P610XXS7FYD1**, OneUI 5.1.1, SPL 2025-04-01 |
| Bootloader | P610XXS7FYD1 — **binary/SWREV 7** (stock firmware must match rev 7) |
| Bootloader state | `flash.locked = 0`, vbmeta `device_state = unlocked`, verified boot **orange**, warranty bit 1 (Knox tripped) — unlock already done by the owner |
| Storage layout | UFS, LUNs sda–sde; **boot = sda12 (59 MiB)**, recovery = sda13, dtbo = sda10, vbmeta = sda22, super = sda25, **userdata = sda32 (≈52 GiB)** |

## CPU / interrupt / timer

| Item | Value | |
| --- | --- | --- |
| CPUs | cpu@0–3 + cpu@100–103 (clusters 0/1, MPIDR 0x0–0x3 / 0x100–0x103) | ✅ |
| GIC | `interrupt-controller@12300000` (base 0x12300000) | ✅ base, ◐ version/reg |
| Arch timer | `timer` node, `use-physical-timer` present, `clock-frequency` property exists — value ◐ (Exynos 9611 platform clock; confirm from DTS) | ◐ |
| MCT | `mct@10040000` | ✅ |
| PSCI | `psci` node present (secondary-core power-up path) | ✅ |
| PMU | `arm-pmu`, `exynos-pmu`, syscon @11860000 | ✅ |

## Storage

| Item | Value | |
| --- | --- | --- |
| UFS host | `ufs@0x13520000` (+ `ufs-srpmb`) | ✅ base, ◐ reg/IRQ |
| Plan | Exynos UFS driver adapted from ios-galaxy-s8, addresses from this map | |

## Display / GPU / input

| Item | Value | |
| --- | --- | --- |
| Display block | `disp_ss@0x14810000`, `decon_f@0x148B0000`, `dsim@0x148E0000` | ✅ |
| Panel | **Himax HX83102E** (`hx83102e`, `decon_board_hx83102e`), 1200×2000 TFT | ✅ |
| GPU | `mali@11500000` — Mali-G72 MP3 (Bifrost); CPU rendering remains the plan (no Metal/AGX on Mali) | ✅ |
| **Touch** | **Himax `himax_ts@0` on SPI `spi@13900000`, CS0** — touch is SPI, not I2C/HSI2C (differs from the S8 port's I2C pattern) | ✅ |
| S Pen | Wacom `wacom@56` on `hsi2c@11D40000` (addr 0x56) — out of scope for early gates | ✅ |
| Buttons | `gpio_keys` node present | ✅ |

## Power

| Item | Value | |
| --- | --- | --- |
| Charger + fuel gauge | **Silicon Mitus SM5713**: `sm5713@49` on `i2c@13840000`, USB-PD `usbpd-5713@33` on `i2c@13830000`, `sm5713-fuelgauge` node, `CONFIG_MUIC_SM5713=y` | ✅ |
| Sub-PMIC | **S2MPB03** `s2mpb03@56` on `i2c@13860000`, 7 LDOs in DT | ✅ |
| PMIC bus | `speedy@11a10000` present (main PMIC on SPEEDY, as on the S8 port; exact part ◐ from DTS) | ✅/◐ |
| Battery (live) | 7040 mAh design (`CHARGE_FULL_DESIGN=7040000`), 65% / charging over USB at dump time, charge counter + current/voltage readable via `/sys/class/power_supply/battery` — a real % driver (Gate 6) reads the SM5713 gauge | ✅ |

## Connectivity / audio / misc

| Item | Value | |
| --- | --- | --- |
| Wi-Fi + BT | **Samsung SCSC** `scsc_wifibt@119c0000`; kernel config platform `"leman_s620_univ"`, firmware in `/vendor/etc/wifi`, `wlan0`/`swlan0` present. No driver precedent in any ios-sweet-family port — Gate 6 research stands | ✅ |
| Audio amp | TI TAS2562 `tas2562@4c` on `hsi2c@11D10000` | ✅ |
| Grip sensor | ABOV A96T3x6 @ `i2c@13880000` addr 0x20 | ✅ |
| RTC | `rtc@11A20000` | ✅ |
| USB | `usb@13200000` (USB3) | ✅ |

## Still owed from Gate 0

- Binary FDT + stock `boot`/`dtbo` images: need root (custom
  recovery session) or the matching stock firmware package
  (P610XXS7FYD1, rev 7) downloaded on the laptop — either route
  also gives the restore-to-Android safety net for Gate 1.
- `dmesg` (blocked for the shell user on stock).
- DT property values marked ◐ above, cross-checked from Samsung's
  kernel DTS.
