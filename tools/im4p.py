#!/usr/bin/env python3
"""Minimal IM4P payload extractor (DER walk, no dependencies).
Usage: im4p.py <file.im4p> <out.bin> — prints the IM4P type string."""
import sys

def rd_len(b, i):
    n = b[i]; i += 1
    if n < 0x80: return n, i
    k = n & 0x7F
    return int.from_bytes(b[i:i+k], 'big'), i + k

def rd_tlv(b, i):
    tag = b[i]; i += 1
    ln, i = rd_len(b, i)
    return tag, b[i:i+ln], i + ln

def main():
    data = open(sys.argv[1], 'rb').read()
    tag, seq, _ = rd_tlv(data, 0)
    assert tag == 0x30, "not a SEQUENCE"
    i = 0
    tag, magic, i = rd_tlv(seq, i); assert magic == b'IM4P', magic
    tag, typ, i = rd_tlv(seq, i)
    tag, desc, i = rd_tlv(seq, i)
    tag, payload, i = rd_tlv(seq, i)
    assert tag == 0x04, "payload not OCTET STRING"
    open(sys.argv[2], 'wb').write(payload)
    print(f"type={typ.decode()} desc={desc.decode()} payload={len(payload)} bytes")

if __name__ == '__main__':
    main()
