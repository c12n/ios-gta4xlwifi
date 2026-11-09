#!/usr/bin/env python3
"""Pack the v1 loader Image + a SWEETXNU payload into a Samsung
boot image (header v2), reusing the verified stock boot.img as the
template: all header addresses, the cmdline and the dtb /
recovery_dtbo sections are preserved, but kernel_size and
ramdisk_size are rewritten to the true sizes and the section
offsets recomputed in 2048-byte pages (unlike the Gate 1 splice,
which kept the stock layout byte-identical).

Usage: pack.py <stock-boot.img> <loader-Image> <payload.bin> <out.img>"""
import struct, sys

def align(n, page):
    return (n + page - 1) & ~(page - 1)

def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def u64(b, o): return struct.unpack_from('<Q', b, o)[0]

def main(stock_p, image_p, payload_p, out_p):
    img = bytearray(open(stock_p, 'rb').read())
    kernel = open(image_p, 'rb').read()
    ramdisk = open(payload_p, 'rb').read()
    assert img[:8] == b'ANDROID!', 'stock magic'
    page = u32(img, 36)
    assert u32(img, 40) == 2, 'header v2 expected'
    hdr_size = u32(img, 1644)
    # locate stock recovery_dtbo + dtb to carry them over
    dtbo_size = u32(img, 1632)
    dtbo_off = u64(img, 1636)
    dtb_size = u32(img, 1648)
    dtbo = bytes(img[dtbo_off:dtbo_off + dtbo_size]) if dtbo_size else b''
    k_size = u32(img, 8)
    r_size = u32(img, 16)
    s_size = u32(img, 24)
    dtb_off_stock = page + align(k_size, page) + align(r_size, page) \
        + align(s_size, page) + (align(dtbo_size, page) if dtbo_size else 0)
    dtb = bytes(img[dtb_off_stock:dtb_off_stock + dtb_size]) if dtb_size else b''

    out = bytearray(img[:page])          # header page, patched below
    out += kernel + b'\0' * (align(len(kernel), page) - len(kernel))
    out += ramdisk + b'\0' * (align(len(ramdisk), page) - len(ramdisk))
    # second_size is 0 in the stock image; assert rather than handle it
    assert s_size == 0, 'stock second stage present - unhandled'
    new_dtbo_off = len(out)
    if dtbo_size:
        out += dtbo + b'\0' * (align(dtbo_size, page) - dtbo_size)
    if dtb_size:
        out += dtb + b'\0' * (align(dtb_size, page) - dtb_size)

    struct.pack_into('<I', out, 8, len(kernel))
    struct.pack_into('<I', out, 16, len(ramdisk))
    struct.pack_into('<Q', out, 1636, new_dtbo_off if dtbo_size else 0)
    assert len(out) <= 61865984, 'exceeds BOOT partition'
    open(out_p, 'wb').write(out)
    print(f'{out_p}: {len(out)} bytes (kernel {len(kernel)}, '
          f'ramdisk {len(ramdisk)}, dtbo {dtbo_size} @ {new_dtbo_off}, '
          f'dtb {dtb_size})')

if __name__ == '__main__':
    main(*sys.argv[1:5])
