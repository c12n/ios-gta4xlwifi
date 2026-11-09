#!/usr/bin/env python3
"""Pack shim.bin into a boot image by replacing the kernel payload
of the verified stock boot.img in place. Header, ramdisk, DTB and
all offsets stay byte-identical to stock; the shim is zero-padded
to the stock kernel size so every section boundary is unchanged."""
import struct, sys

STOCK = "../../firmware/extracted/ap/boot.img"
OUT = "boot-shim-v0.img"

img = bytearray(open(STOCK, "rb").read())
shim = open("shim.bin", "rb").read()
assert img[:8] == b"ANDROID!", "stock image magic"
kernel_size, page_size = struct.unpack_from("<I", img, 8)[0], struct.unpack_from("<I", img, 36)[0]
assert len(shim) <= kernel_size, f"shim {len(shim)} > kernel slot {kernel_size}"
img[page_size:page_size + kernel_size] = shim + b"\x00" * (kernel_size - len(shim))
open(OUT, "wb").write(img)
print(f"{OUT}: {len(img)} bytes (shim payload {len(shim)} bytes at offset {page_size})")
