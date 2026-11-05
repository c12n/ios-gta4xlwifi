#!/usr/bin/env python3
"""Minimal FDT (flattened device tree) dumper: DTB -> readable DTS text.
No external dependencies. Usage: fdt_dump.py <file.dtb> [out.dts]"""
import struct, sys

FDT_MAGIC=0xd00dfeed; BEGIN=1; END_NODE=2; PROP=3; NOP=4; END=9

def parse(data):
    magic, total, off_struct, off_strings, off_rsv, ver, compat, bootcpu, len_strings, len_struct = struct.unpack_from(">10I", data, 0)
    assert magic == FDT_MAGIC, hex(magic)
    strings = data[off_strings:off_strings+len_strings]
    def getstr(off):
        end = strings.index(b"\x00", off)
        return strings[off:end].decode("utf-8", "replace")
    lines = []
    pos = off_struct; end_struct = off_struct + len_struct
    depth = 0; path = []
    def fmtval(raw):
        # try string(s)
        if raw and all(32 <= b < 127 or b in (0,) for b in raw) and raw.endswith(b"\x00"):
            parts = raw.rstrip(b"\x00").split(b"\x00")
            try:
                ss = [p.decode() for p in parts]
                return ", ".join(f'"{s}"' for s in ss)
            except UnicodeDecodeError:
                pass
        if len(raw) % 4 == 0 and len(raw) > 0:
            cells = struct.unpack(f">{len(raw)//4}I", raw)
            return "<" + " ".join(f"0x{c:x}" for c in cells) + ">"
        return "[" + " ".join(f"{b:02x}" for b in raw) + "]"
    while pos < end_struct:
        tok, = struct.unpack_from(">I", data, pos); pos += 4
        if tok == BEGIN:
            end = data.index(b"\x00", pos)
            name = data[pos:end].decode("utf-8", "replace")
            pos = (end + 4) & ~3
            lines.append("  "*depth + (name if name else "/") + " {")
            path.append(name); depth += 1
        elif tok == END_NODE:
            depth -= 1; path.pop()
            lines.append("  "*depth + "};")
        elif tok == PROP:
            ln, nameoff = struct.unpack_from(">2I", data, pos); pos += 8
            raw = data[pos:pos+ln]; pos += (ln + 3) & ~3
            pname = getstr(nameoff)
            lines.append("  "*depth + (f"{pname} = {fmtval(raw)};" if ln else f"{pname};"))
        elif tok == NOP:
            continue
        elif tok == END:
            break
        else:
            raise ValueError(f"bad token {tok} at {pos-4:#x}")
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    out = parse(open(sys.argv[1], "rb").read())
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(out)
    sys.stdout.write(out)
