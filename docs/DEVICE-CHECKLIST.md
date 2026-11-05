# Device session checklist — Gate 0 (first plug-in)

Tablet: Galaxy Tab S6 Lite Wi-Fi 2020 (SM-P610). Goal of this
session: **dumps only**. Nothing is flashed, nothing is unlocked,
nothing is wiped in this session.

## Before plugging in

- [ ] Tablet charged above 50%
- [ ] A laptop Muse can drive remotely (MSI/Windows preferred —
      Odin lives there later; Mac also fine for dumps via ADB)
- [ ] USB-C cable that carries data (not charge-only)
- [ ] Know the tablet's current Android build (Settings > About —
      screenshot is enough)

## Session steps

1. Enable Developer Options + USB debugging on the tablet; accept
   the ADB prompt when the laptop connects.
2. Run `tools/gta-dump.sh` — pulls the live FDT, getprop, partition
   list, kernel config, dmesg, bus/input/power-supply listings.
3. Record in NOTES.md: model, build fingerprint, bootloader version.
4. Identify from the FDT (this decides most of the port):
   GIC version/base, timer frequency, UFS controller, DECON/panel,
   touch controller chip, PMIC + fuel gauge, Wi-Fi chip.
5. Back up the stock firmware reference (exact build) so Android
   can always be restored with Odin.

## NOT in this session (needs the owner present and agreeing)

- Bootloader unlock — **wipes all data, trips Knox permanently**,
  cannot be undone.
- Flashing the BOOT partition (Gate 1).
- Writing the iOS root image to USERDATA (Gate 3) — erases Android
  user data.
