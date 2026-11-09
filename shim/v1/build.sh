#!/bin/bash
# Build the gta4xlwifi XNU loader (Samsung S-Boot "kernel" Image).
# Produces out/Image only; packing into a v2 boot image is pack.py's
# job (the dreamlte v0/DTBH packer does not apply to this device).
set -euo pipefail
cd "$(dirname "$0")"
CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -fno-tree-loop-distribute-patterns -march=armv8-a -Wall -Wextra -Werror"
mkdir -p out
$CC $CFLAGS -c start.S -o out/start.o
$CC $CFLAGS -c loader.c -o out/loader.o
$CC $CFLAGS -c fdt.c -o out/fdt.o
objs="out/loader.o out/fdt.o"
# Runs wherever S-Boot puts it with no relocation pass.
abs=$(aarch64-linux-gnu-readelf -r $objs | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations" >&2; exit 1; }
$CC $CFLAGS -static -T loader.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o $objs -o out/loader.elf
$OBJCOPY -O binary out/loader.elf out/Image
size=$((16#$(aarch64-linux-gnu-nm out/loader.elf | awk '$3=="_end"{print $1}')))
truncate -s "$size" out/Image
echo "out/Image: $(stat -c %s out/Image) bytes"
