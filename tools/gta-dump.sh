#!/usr/bin/env bash
# gta-dump.sh — Gate 0 device dump for gta4xlwifi (SM-P610).
#
# READ-ONLY: pulls hardware facts over ADB. Flashes nothing, writes
# nothing to the device. Run once in Android (USB debugging on) and,
# if possible, once in a custom recovery with adb root for the items
# marked [root] (boot image, full partition images).
#
# Usage:  ./tools/gta-dump.sh [output-dir]
# Output: a timestamped folder under dumps/ (gitignored content —
# it contains device-identifying data; do NOT commit it).
set -euo pipefail

OUT="${1:-dumps/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"
echo "Writing dump to $OUT"

adb wait-for-device
{
  echo "=== getprop ==="
  adb shell getprop
} > "$OUT/getprop.txt" 2>&1 || true

# The single most valuable file: the device tree Android booted with.
adb pull /sys/firmware/fdt "$OUT/live.fdt" 2>/dev/null \
  || adb shell "cat /sys/firmware/fdt" > "$OUT/live.fdt" 2>/dev/null \
  || echo "live FDT not readable without root — retry in recovery" > "$OUT/live.fdt.MISSING"

adb shell "ls -l /proc/device-tree/ 2>/dev/null; cat /proc/cmdline" > "$OUT/proc-dt.txt" 2>&1 || true
adb shell "ls -l /dev/block/by-name/ 2>/dev/null; cat /proc/partitions" > "$OUT/partitions.txt" 2>&1 || true
adb shell "cat /proc/cpuinfo; echo; cat /proc/meminfo" > "$OUT/cpu-mem.txt" 2>&1 || true
adb shell "zcat /proc/config.gz 2>/dev/null" > "$OUT/kernel-config.txt" 2>&1 || true
adb shell dmesg > "$OUT/dmesg.txt" 2>&1 || true
# Chip identification helpers: I2C/SPI buses, input devices, wifi firmware
adb shell "ls /sys/bus/i2c/devices/ 2>/dev/null; echo ---; ls /sys/bus/spi/devices/ 2>/dev/null; echo ---; cat /proc/bus/input/devices 2>/dev/null" > "$OUT/buses-input.txt" 2>&1 || true
adb shell "ls /sys/class/power_supply/ 2>/dev/null; for d in /sys/class/power_supply/*/; do echo == \$d; cat \$d/type \$d/uevent 2>/dev/null; done" > "$OUT/power.txt" 2>&1 || true

# [root] Stock boot image — only works with adb root (recovery).
if adb shell "id" 2>/dev/null | grep -q "uid=0"; then
  BOOTDEV="$(adb shell "readlink -f /dev/block/by-name/boot" | tr -d '\r')"
  echo "Pulling stock boot from $BOOTDEV"
  adb shell "dd if=$BOOTDEV of=/tmp/stock-boot.img bs=4M" && adb pull /tmp/stock-boot.img "$OUT/stock-boot.img" || true
else
  echo "No adb root: stock boot image still owed (pull it in recovery)." > "$OUT/stock-boot.img.MISSING"
fi

echo "Done. Record the build fingerprint from getprop.txt in NOTES.md,"
echo "then decompile live.fdt (dtc -I dtb -O dts) into device/ notes."
