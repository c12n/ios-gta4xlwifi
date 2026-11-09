#!/bin/bash
# Build shim v0.1 and pack it as an Android boot image by replacing
# the kernel payload inside the verified stock boot.img in place
# (identical header + layout; shim zero-padded to stock kernel size).
set -euo pipefail
cd "$(dirname "$0")"
CC=aarch64-linux-gnu-gcc
$CC -c -ffreestanding -nostdlib -O2 -o start.o start.S
$CC -c -ffreestanding -nostdlib -O2 -o main.o main.c
$CC -nostdlib -T link.ld -o shim.elf start.o main.o
aarch64-linux-gnu-objcopy -O binary shim.elf shim.bin
python3 pack.py
