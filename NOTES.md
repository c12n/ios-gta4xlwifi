# NOTES — engineering log

Every boot attempt, crash and decision, in order. Newest at the top
of each day's section. Log excerpts belong here, not in issues.

## 2026-11-05 — project start

- Project created: staged port (boot first) approved; full feature
  list (touch, Wi-Fi, charging/battery, GPU, all cores) is the
  long-term target — see PORTING.md gates.
- Timeframe updated by the owner later on 2026-11-05: **unlimited**
  (replacing the original two-week window). No deadline pressure;
  gates are cleared in order, however long each takes. Wi-Fi and
  Mali GPU remain research items in Gate 6, not guarantees.
- Bases chosen: ios-sweet (generic layer) + ios-galaxy-s8 (Exynos
  layer, pointed out by the project owner today — it reaches the
  lock screen on Exynos 8895, which materially improves the Exynos
  starting position vs. the Galaxy S7 precedent).
- Key facts carried in from the S8 port: GIC-400 (not v3), 4 KiB
  pages, own Exynos UFS driver, S-Boot framebuffer via DECON,
  loader in the BOOT partition, log via ramoops + USERDATA ring,
  Mali GPUs cannot run iOS Metal/AGX — CPU rendering is the plan.
- Repo skeleton written locally; public GitHub repo creation in
  progress (connector cannot create repos; browser route).
- Next: Gate 0 device dumps when the tablet is plugged into the
  owner's laptop. Nothing has been flashed; the tablet is untouched.

### Gate 0 session — 2026-11-05 ~09:20 CST (dumps only, nothing flashed)

- Owner plugged the tablet into the MSI laptop (Tailscale + SSH
  verified); ADB sees **SM-P610 / gta4xlwifi** directly.
- Owner had already unlocked: OEM unlocking on, bootloader
  unlocked (`flash.locked=0`, vbmeta unlocked, verified boot
  orange, Knox warranty bit 1). Build **P610XXS7FYD1**
  (Android 13, bootloader rev 7), battery 65% charging.
- Captured locally (never committed — serials inside): getprop,
  kernel config, partition table (boot=sda12 59 MiB,
  userdata=sda32 ≈52 GiB), full `/proc/device-tree` node map,
  battery/power-supply data.
- Chips identified from the live tree — full detail in
  `research/HARDWARE-MAP.md`: GIC @0x12300000, UFS @0x13520000,
  Mali-G72 @0x11500000, DECON @0x148B0000 + Himax HX83102E panel,
  **touch = Himax on SPI @0x13900000 (not I2C)**, Wacom S Pen on
  HSI2C, **SM5713** charger/fuel-gauge, S2MPB03 sub-PMIC, SPEEDY
  bus, **Samsung SCSC (leman_s620) Wi-Fi/BT**, PSCI + 8 CPUs.
- Blocked on stock (shell user): binary FDT (`/sys/firmware/fdt`
  is 0400 root), DT property values, dmesg, stock boot/dtbo
  images. Routes: custom-recovery session or the rev-7 stock
  firmware package on the laptop. Gate 0 is otherwise complete.

### AFK session — 2026-11-05 ~09:25–09:42 CST (owner away, no flashing)

- Owner approved the stock-firmware download, then went AFK.
  Tablet's CSC read from getprop: **XAC**. Firmware package
  confirmed: P610XXS7FYD1 / P610OXM7FYD1, Bit 7, 4.9 GB
  (child files: AP 4.41 GB, BL 2.44 MB, CSC ~230 MB).
- Download walls, in order: samloader version check 403;
  samloader FUS nonce auth broken vs current Samsung servers
  (411 Content-Length patch applied locally, then nonce key
  derivation fails — tool unmaintained); SamFW in the browser —
  page loads and reconfirms the package, but the download button's
  invisible Cloudflare Turnstile failed the automated browser
  6 times. Owner click may pass; otherwise Frija at Gate 1.
- Board DTBO overlays mined from the LineageOS kernel tree:
  touch = Himax hxcommon, SPI 7 MHz, 1200×2000, HX83102E fw —
  folded into HARDWARE-MAP.md. SoC base tree is a Samsung-prebuilt
  DTB, so base property values still wait on the stock boot image.
- Owner put the tablet in **Download Mode**; verified from the
  MSI: ADB gone (expected), Windows shows SAMSUNG USB CDC
  Composite (VID_04E8/PID_685D, OK) — Odin path + drivers proven
  for Gate 1. Nothing flashed. Odin protocol is write-only, so
  download mode yields no partition readback.

### Wall protocol + firmware breakthrough — 2026-11-05 ~09:54–10:20 CST

- Owner directed the AI pack (Claude Opus 5.5 Max / Gemini 3.1 Pro
  High / DeepSeek DeepThink+Search) on both walls. Full scored
  synthesis: `research/AI-PACK-SYNTHESIS-GATE0.md`.
- **Firmware wall broken**: `topjohnwu/samloader-rs` v2.2.0 talks
  to Samsung's current (Smart Switch) endpoints — check-update
  returned the exact XAC string and the 4.9 GB package download
  started 10:00 CST. Root causes for old samloader: UA-filter 403
  + rotated nonce key (Claude's diagnosis, matches local evidence).
  Gemini's Bifrost-CLI-jar claim was fabricated (404) — caught by
  verification, not used.
- **Base DT values resolved** from Samsung's `exynos9610.dts`
  (LineageOS lineage-23.2): GIC-400 ranges, timer 26 MHz (CNTFRQ
  unprogrammed by S-Boot), MCT, UFS `samsung,exynos-ufs` windows +
  SPI 157, PSCI smc ids, SYSTEM_RESET treated as unsupported with
  PMU SWRESET @0x11860400 fallback. HARDWARE-MAP.md updated.
- **Firmware download DONE 10:38 CST** (5,259,729,313 B decrypted
  zip). MD5 `4256abdb9bd6a333fabf3b88cd149936` — **SamMobile's
  hash was right; SamFW's was wrong** for Samsung's own file.
  BL + AP `.tar.md5` checksums verify (samloader-rs verify-md5).
- **Gate 0 fully closed ~11:40 CST**: boot.img is exactly 59 MiB
  (= sda12), header v2; base DTB extracted from offset 33519680
  (135,192 B) and decompiled with a new in-repo tool
  (`tools/fdt_dump.py`, dependency-free FDT dumper): **the blob
  matches exynos9610.dts on every checked value** (GIC, timer
  0x18cba80, MCT, UFS windows + SPI 157, PSCI). DTBO: 5 overlays,
  all gta4xl; stock overlay confirms Himax touch (coords
  1200×2000) and the **S-Boot framebuffer reservation
  0xCA000000/20 MiB** — the early-display handover target.
  Decompiled trees in `dumps/20261105-gate0/firmware-extract/`
  (local only).

## Template for boot entries

### Boot NNN — YYYY-MM-DD HH:MM
- Build: <kernel commit / patch set / boot-args>
- Change vs last boot: <one thing>
- Result: <how far it got, verbatim log lines that matter>
- Next: <one next step>
