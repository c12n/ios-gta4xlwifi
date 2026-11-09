# Hardware map — gta4xlwifi (SM-P610, Exynos 9611)

Source: **live Gate 0 dumps from the actual tablet**, 2026-11-05
(Android 13, build P610XXS7FYD1), taken over ADB via the owner's
MSI laptop. Raw dumps stay local (they contain the device serial);
this file carries only hardware facts.

Legend: ✅ = read directly off the device. ◐ = node presence and
address confirmed on-device; property values (reg ranges, IRQ
numbers, clock rates) still to be confirmed — property *files*
under `/proc/device-tree` are not readable by the Android shell
user, and `/sys/firmware/fdt` is root-only (0400) on stock firmware.
**Update 2026-11-05 (later):** most ◐ values are now ✅-sourced
from Samsung's own base device tree, `arch/arm64/boot/dts/exynos/
exynos9610.dts` (the 9610 base is reused verbatim for the 9611;
fetched from LineageOS android_kernel_samsung_gta4xl lineage-23.2)
— marked ✅(blob) below. Full pack cross-check:
`research/AI-PACK-SYNTHESIS-GATE0.md`.
**Update 2026-11-05 (final):** the stock firmware was downloaded
from Samsung's servers (samloader-rs) and the **actual base DTB
was extracted from boot.img and decompiled** (boot header v2, DTB
at offset 33519680, 135192 bytes; 5 DTBO overlays alongside).
**Every ✅(blob) value below matches the real blob exactly** —
marked ✅(blob). Decompiled trees are kept locally under
`dumps/20261105-gate0/firmware-extract/` (not in git).

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
| GIC | **GIC-400** (GICv2), compatible `arm,cortex-a15-gic`/`arm,cortex-a9-gic`; reg: **GICD 0x12301000/0x1000, GICC 0x12302000/0x1000, GICH 0x12304000/0x2000, GICV 0x12306000/0x2000** (note: real GICC is 8 KiB, GICC_DIR at 0x12303000 — DTS lists 4 KiB) | ✅(blob) |
| Arch timer | `arm,armv8-timer`, **clock-frequency 26000000 (26 MHz)**, PPIs 13/14/11/10 level-low; ~~CNTFRQ_EL0 is NOT programmed by S-Boot~~ — **CORRECTED 2026-11-09 by the shim v0.1 on-device probe: CNTFRQ_EL0 reads 0x018CBA80 = 26,000,000** (an early boot stage does program it; the ADT still carries timebase-frequency 26000000) | ✅(blob) + probe |
| MCT | `mct@10040000`, compatible `samsung,exynos4210-mct`, reg size 0x800, 12 IRQs | ✅(blob) |
| PSCI | `arm,psci`, **method `smc`**; CPU_SUSPEND 0xC4000001, CPU_OFF 0x84000002, CPU_ON 0xC4000003. **SYSTEM_RESET/OFF/VERSION unsupported until proven otherwise** — reset fallback: write 1 to PMU SWRESET @0x11860400 | ✅(blob) |
| PMU | `arm-pmu`, `exynos-pmu`, syscon @11860000 (SWRESET at 0x11860400) | ✅ |

## Storage

| Item | Value | |
| --- | --- | --- |
| UFS host | `ufs@0x13520000` (+ `ufs-srpmb`), compatible **`samsung,exynos-ufs`** (mainline's `exynos7-ufs` is a different binding — do not use); reg: **HCI 0x13520000/0x200, vendor 0x13521100/0x200, UniPro 0x13510000/0x8000, protector 0x13530000/0x100**; IRQ **SPI 157** (INTID 189); HCI version not in DT — read VER @0x13520008 on hw (expect 2.1); downstream quirks: PRDT byte-granular, broken REQ_LIST_CLR, 9610-specific PHY cal | ✅(blob) |
| Plan | Exynos UFS driver adapted from ios-galaxy-s8, addresses/quirks from this map | |

## Display / GPU / input

| Item | Value | |
| --- | --- | --- |
| Display block | `disp_ss@0x14810000`, `decon_f@0x148B0000` (compatible `samsung,exynos9-decon`, reg 0x148B0000/0x10000, first IRQ SPI 199), `dsim@0x148E0000` | ✅ / ✅(blob) |
| RAM (live) | Banks 0x80000000, 0xC0000000, 0xE1900000, 0x880000000 (from the live tree; the base blob's memory nodes are the generic 2 GiB×3 placeholders — S-Boot fixes them up per unit) | ✅ |
| Framebuffer reservation | `framebuffer@0xCA000000`, reg 0xCA000000 size 0x1400000 (20 MiB), compatible `exynos,fb_rmem` — S-Boot's handover framebuffer (logo); the early-display target for Gates 2/4. In the DTBO overlays, not the base blob | ✅(blob) |
| Initrd window | chosen: linux,initrd 0x84000000–0x841FFFFF (bootargs empty in blob) | ✅(blob) |
| Panel | **Himax HX83102E** (`hx83102e`, `decon_board_hx83102e`), 1200×2000 TFT | ✅ |
| GPU | `mali@11500000` — Mali-G72 MP3 (Bifrost); CPU rendering remains the plan (no Metal/AGX on Mali) | ✅ |
| **Touch** | **Himax `himax_ts@0` on SPI `spi@13900000`, CS0** — touch is SPI, not I2C/HSI2C (differs from the S8 port's I2C pattern). From the board DTBO (LineageOS kernel tree): compatible `himax,hxcommon`, SPI max 7 MHz, panel coords 1200×2000, touch firmware `tsp_himax/hx83102e_gta4xl.fw` (HX83102E TDDI family, same as the panel), IRQ on GPA0-0, reset on GPG1-4 | ✅ |
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
  (P610XXS7FYD1, rev 7) — either route also gives the
  restore-to-Android safety net for Gate 1.
  Firmware identity confirmed 2026-11-05: CSC of the tablet is
  **XAC** (Canada), package = PDA **P610XXS7FYD1** / CSC
  **P610OXM7FYD1** (OXM multi-CSC), ~4.9 GB. Child files (SamFW):
  AP zip 4.41 GB, **BL zip only 2.44 MB**, CSC/HOME_CSC ~230 MB
  each. MD5 discrepancy to resolve at download time: SamFW's XAC
  page lists full-file MD5 `84c58e754d1a54e73f9ed473b762a20f`,
  SamMobile lists `4256abdb9bd6a333fabf3b88cd149936` for other OXM
  regions — trust the inner `.tar.md5` checksums after download,
  not either page.
  Download attempts so far: samloader's version check 403s and its
  FUS nonce auth fails against Samsung's current servers (patched
  the 411 Content-Length issue; nonce key derivation then breaks —
  the tool is unmaintained against the new auth). SamFW via
  browser (2026-11-05): firmware page loads and confirms all of
  the above, but its download button is gated by an invisible
  Cloudflare Turnstile that failed verification 6 times for the
  automated browser (possibly the site's daily bot limit) — a
  human click in the same browser may pass. Remaining routes:
  owner clicks through SamFW, or Frija on the MSI during the
  Gate 1 session.
- `dmesg` (blocked for the shell user on stock).
- DT property values: **resolved 2026-11-05** — first from
  Samsung's `exynos9610.dts` base tree, then **confirmed against
  the real DTB extracted from the downloaded stock boot.img**
  (every value identical). The downloaded package is also the
  Gate 1 restore safety net; its zip MD5 is
  `4256abdb9bd6a333fabf3b88cd149936` (SamMobile's listing was
  correct; SamFW's listed hash does not match Samsung's file).
