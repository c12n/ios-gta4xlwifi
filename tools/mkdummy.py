#!/usr/bin/env python3
"""Build a hand-rolled SWEETXNU v1 container around the dummy stub
for the Gate 2 loader smoke test (mkpayload.py needs a real Mach-O;
the loader only reads this container's own fields).

Layout per shim/v1/loader.c struct payload: header 0x2a8 bytes
incl. one segment entry, then segment bytes, then the ADT blob
(here a 4 KiB dummy - the loader copies but never parses it)."""
import struct, sys

VIRT_BASE = 0xFFFFFE0000000000
PHYS_BASE = 0x880000000
MEM_SIZE = 0x1000000            # 16 MiB smoke window (loader zeroes it)

def main(stub_path, out_path):
    stub = open(stub_path, 'rb').read()
    stub = stub + b'\0' * (-len(stub) % 8)
    hdr_size = 0x2a8 + 32       # header + one segment entry
    seg_off = hdr_size
    adt_off = seg_off + len(stub)
    adt = bytearray(0x1000)
    adt[:8] = b'DUMMYADT'
    kernel_end = VIRT_BASE + len(stub)
    cmdline = b'dummy smoke test\0'
    cmdline = cmdline + b'\0' * (608 - len(cmdline))
    hdr = struct.pack('<8sII', b'SWEETXNU', 1, 1)
    hdr += struct.pack('<6Q', VIRT_BASE, VIRT_BASE, adt_off, len(adt),
                       kernel_end, PHYS_BASE)
    hdr += struct.pack('<Q', MEM_SIZE)
    hdr += cmdline
    hdr += struct.pack('<4Q', VIRT_BASE, len(stub), seg_off, len(stub))
    assert len(hdr) == hdr_size, len(hdr)
    open(out_path, 'wb').write(hdr + stub + bytes(adt))
    print(f'{out_path}: {hdr_size + len(stub) + len(adt)} bytes '
          f'(stub {len(stub)}, adt {len(adt)})')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
