# ios-gta4xlwifi

**Apple's iOS 16 running on a Samsung Galaxy Tab S6 Lite Wi-Fi (2020).**

This project ports Apple's open-source XNU kernel (xnu-8796, the iOS 16
generation) to the Samsung Galaxy Tab S6 Lite Wi-Fi 2020 (`gta4xlwifi`,
SM-P610, Samsung Exynos 9611). On top of it runs the **unmodified
iOS 16.7.16 (20H392) userland of the iPhone X**: launchd, the system
daemons, backboardd, SpringBoard and the stock apps.

It is a port of [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet)
(Redmi Note 10 Pro, Qualcomm SM7150 / Snapdragon 732G), following the
porting approach documented at [hackiosx.dev](https://hackiosx.dev/).
See `CREDITS.md` for what comes from where, and under which licence.

> **Experimental bring-up, not a usable tablet OS.** Many things are
> missing or stubbed, and Apple's security model is mostly switched off.
> Samsung devices have no `fastboot boot`: the loader is flashed to the
> BOOT partition with Odin/Heimdall. Installing the iOS system erases
> Android's user data. Unlocking the bootloader wipes the device and
> trips Knox permanently. Use a spare device, back up first, and do not
> put personal data on it.

## Target device

| | |
| --- | --- |
| Device | Samsung Galaxy Tab S6 Lite Wi-Fi (2020) |
| Models | SM-P610, SM-P610N |
| Codename | `gta4xlwifi` (board family `gta4xl`, SoC platform `universal9611`) |
| SoC | Samsung Exynos 9611 (10 nm) |
| CPU | 4x Cortex-A73 @ 2.3 GHz + 4x Cortex-A53 @ 1.7 GHz (ARMv8, no pointer authentication) |
| GPU | ARM Mali-G72 MP3 (Bifrost) |
| RAM | 4 GB LPDDR4X |
| Display | 10.4" TFT LCD, 1200 x 2000 |
| Storage | 64 / 128 GB + microSD |
| Battery | 7040 mAh, 15 W wired charging |

The LTE model (SM-P615, `gta4xl`) is **not** a target of this repo yet.

## Status

Staged bring-up. Gates, in order — each must work before the next means
anything:

| Gate | What | State |
| --- | --- | --- |
| 0 | Device dumps: stock boot image, live FDT, partitions, chip IDs | **Next — awaiting device session** |
| 1 | Our own code (shim) runs from the BOOT partition via Odin/Heimdall | Not started |
| 2 | XNU early boot: framebuffer console + recoverable kernel log | Not started |
| 3 | Exynos storage driver -> HFS+ root -> launchd | Not started |
| 4 | Display copy + touch -> lock screen / home screen | Not started |
| 5 | SMP: secondary cores online | Not started |
| 6 | Stretch: real battery % / charging, then Wi-Fi, then GPU | Not started |

Honest expectations: hackiosx.dev rates Samsung Exynos the hard
category ("every driver is new"). The closest Exynos precedent
(Galaxy S8, Exynos 8895, ios-galaxy-s8) reaches the lock screen with
CPU rendering; the Galaxy S7 port reaches the setup screen.
The base project itself has no Wi-Fi, no GPU driver and a static
battery readout on its native Snapdragon hardware. This project has
no fixed deadline — work proceeds gate by gate for as long as it
takes. That does not make Wi-Fi or a Mali-G72 GPU driver easy:
both remain research items with no precedent in this family of
ports, pursued in Gate 6 after boot, display, touch and SMP work.

Full plan and hardware notes: `PORTING.md`, `NOTES.md`,
`research/HARDWARE-MAP.md`.

## How it will boot (planned)

```
Samsung bootloader (unlocked, BOOT partition flashed via Odin/Heimdall)
  -> shim: own MMU setup, reads the live FDT, loads the payload
     -> XNU Mach-O + generated Apple Device Tree (ADT) + boot-args
        -> XNU -> storage driver -> HFS+ root in the userdata partition
           -> dyld + shared cache -> launchd -> daemons -> backboardd + SpringBoard
```

## Repository layout

| Path | What |
| --- | --- |
| `shim/` | Bare-metal boot shim (C + asm), packed for the Samsung BOOT partition |
| `xnu/` | XNU patch series for gta4xlwifi (on top of the ios-sweet series) |
| `tools/` | ADT builder, payload packer, root-image builder, log puller, device dump script |
| `device/` | gta4xlwifi hardware constants, FDT/ADT notes |
| `research/` | Hardware map and reference material |
| `docs/` | Device session checklist and procedures |
| `NOTES.md` | Engineering log: every boot, crash and decision |
| `PORTING.md` | The staged porting plan |

Not in git: partition backups, live device trees, recovery images,
Apple firmware and root images, and downloaded or generated build
trees. They contain device serials and calibration data, or Apple's
copyrighted files. `.gitignore` already excludes them.

## Copyright

Copyright (c) 2026 c12n Apps. See `LICENSE` and `CREDITS.md`.
This project is not affiliated with, endorsed by, or sponsored by
Apple Inc. or Samsung. iOS and iPhone are trademarks of Apple Inc.
