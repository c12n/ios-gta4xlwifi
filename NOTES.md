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

## Template for boot entries

### Boot NNN — YYYY-MM-DD HH:MM
- Build: <kernel commit / patch set / boot-args>
- Change vs last boot: <one thing>
- Result: <how far it got, verbatim log lines that matter>
- Next: <one next step>
