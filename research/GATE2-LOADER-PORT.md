# Gate 2 loader port — gap analysis: dreamlte (Galaxy S8) to gta4xlwifi

Produced 2026-11-09 from the local clones of ios-sweet and
ios-galaxy-s8 plus the v0.1 probe results (boot CPU = A73
MPIDR 0x0 @ EL1, CNTFRQ_EL0 = 0x018CBA80 = 26 MHz programmed).

**Correction to GATE2-DESIGN.md's loader summary:** the
dreamlte loader builds *no* page tables. It runs the entire
load with the MMU off, using volatile Device-memory copies.
Temp page tables exist only in the Qualcomm lineage (16K
granule) and the A5 ancestor. Porting dreamlte means we need
**no MMU code at all** for Gate 2.

## Inventory (what the dreamlte build actually compiles)

- `shim/dreamlte/start.S` (2,351 B): ARM64 Image header +
  entry; saves x0/CurrentEL/SCTLR, image-relative SP + VBAR,
  zeroes BSS, calls dl_main, MMU/caches-off XNU handoff.
- `shim/dreamlte/loader.c` (14,303 B): dl_main — dual-zone
  ramoops log + FB console, SWEETXNU payload parse/validate,
  window zero, segment copy, ADT + rev-2 boot_args placement,
  entry-marker reservation, dl_exception. Payload and
  boot_args structs are defined inline (layout pinned by
  _Static_asserts: segments at 0x2a8, boot_args = 736 B,
  CommandLine at offset 108).
- `shim/dreamlte/loader.ld`: links at 0 (PIC), 0x8000 stack
  reserved inside the image.
- `shim/dreamlte/build.sh`: strict flags, **fails on any
  ABS64 relocation** (PIC gate), pads Image to _end.
- Probes (all dropped for Gate 2): pmic.c (S2MPS17 over
  SPEEDY 0x15b50000 — our PMIC differs entirely), smp_probe.c
  (returns Gate 5), ufs_probe.c (returns Gate 3 with our
  addresses), touch_probe.c + battery_probe (SPI Himax /
  SM5713 here — rewritten fresh at Gates 4/6),
  display_probe.c (diagnostic only).
- Shared: `shim/fdt.c` (fdt_chosen_u64 only), `shim/font.h`
  (8x16 font). Everything else in ios-galaxy-s8/shim/ is the
  untouched Qualcomm original — byte-identical to ios-sweet.
  The dreamlte loader touches **no GIC registers**; loader
  interrupt work is daifset + VBAR only.
- Host: tools/mkpayload.py (SWEETXNU v1; takes phys_base /
  mem_size from the ADT /chosen dram values; unslides
  LC_DYLD_CHAINED_FIXUPS), tools/adt.py, tools/mkadt.py +
  mkadt_dreamlte.py layering (our mkadt_gta4xl.py follows).

## Board deltas that matter (S8 -> gta4xlwifi)

All loader constants live in dreamlte/loader.c:24-42.

- FB 0xcc000000 1440x2960 -> **0xCA000000, 1200x2000**,
  stride FB_W*4 = 4800.
- DECON trigger unmask (write 0x1281 -> 0x12860070): **drop**
  — video mode here; Gate 1 proved no poke needed.
- Ramoops console 0x92080000/0x80000, pmsg 0x92180000,
  marker = console_base + size - 0x1000 (0x920ff000):
  **relocate into our high bank above the XNU window**
  (window ends 0x8A0000000; bank ends 0x900000000). Marker
  value must match A5_ENTRY_MARKER_PHYS in patch 0125.
- Low-RAM initrd bound 0x80000000-0xbc800000 ->
  **end 0xBAB00000** (live-DT bank 0 size 0x3AB00000).
- XNU RAM window: base 0x880000000 / end 0x900000000 are
  **identical for us** (same bank geometry); the 512 MiB
  window size comes from the ADT via mkpayload.
- Link at 0, PIC + ABS64 gate, image-relative stack: adopt
  (our v0.1 absolute link worked twice, but PIC removes the
  failure class).
- PMIC/RTC (s8rtc= boot-arg), touch rails: drop; our SPEEDY
  is at 0x11a10000 with a different PMIC. RTC returns as
  post-Gate-2 polish.
- GIC (ADT side): S8 offsets 0x0201000/0x0202000 under
  arm-io/ranges base 0x10000000 -> ours **0x2301000 /
  0x2302000** (GICD 0x12301000, GICC 0x12302000).
- UFS (Gate 3): S8 0x11120000/0x11121100/0x11130000 ->
  ours **0x13520000 / 0x13521100 / 0x13530000**.
- PMU (Gate 5): S8 0x16480000 -> ours **0x11860000**;
  CPU_CONFIGURATION offset formula must be verified
  against ~/workspace/kernel-gta4xl exynos-pmu.c first.
- Boot CPU: S8 A53 MPIDR 0x100 -> ours **A73 MPIDR 0x0**
  (ADT logical CPU 0 mapping + 0125 macro; loader agnostic).
- FDT /chosen: code reusable unchanged. **Highest port
  risk:** whether S-Boot's v2 flow populates
  linux,initrd-start/end is unverified. Fallback constant:
  rd_start = **0x81000000** (header ramdisk_addr 0x11000000
  + Samsung 0x70000000).
- Boot image: S8 packer (v0 + DTBH + SEANDROIDENFORCE) is
  **not usable**; extend our pack.py: v2 header preserved,
  kernel_size/ramdisk_size rewritten to true sizes — kernel
  slot = loader Image (~100 KB, NOT padded to the 32 MB
  stock slot), ramdisk slot = payload.bin. Total ~21 MB,
  well under the 59 MiB BOOT partition.
- Loader PAGE_SIZE stays 4096 (XNU-side; distinct from the
  boot image's 2048 and mkpayload's 0x4000 Mach-O page).
- First-trial boot-args verbatim from make-boot.sh:
  `debug=0xc serial=3 cpus=1 keepsyms=1
  -enable_kprintf_spam -noprogress wdt=-1
  wdt_test=no_user_checkin a5touchprobe=0`
- Loader failure text must say POWER+VOL UP -> Lineage
  recovery (no Bixby, no TWRP).
- EL1 hard check in dl_main: keep (probe-verified EL1).

## Entry-state deltas (S-Boot 8895 vs 9611)

- x0 = DTB: S8's DTB sits at 0x8A000000; ours is expected
  at **0x87000000** (header dtb_addr 0x10000000 + 0x70000000).
  v0/v0.1 clobbered x0 instantly; v1 must capture it first
  (their mov x19, x0) and log it; fdt magic check validates.
- v1 must also capture CurrentEL, SCTLR_EL1, MPIDR_EL1 for
  the log line, install VBAR + dl_exception vectors, and
  zero BSS (loader.c has real statics).
- MMU off at entry; dirty RAM assumed -> keep the
  unconditional 512 MiB window zeroing (expect the
  "zeroing XNU RAM..." line to sit a while: MMU-off
  device-memory copies of ~530 MB total are slow; normal).

## Risks (top)

1. /chosen initrd under header v2 (above).
2. PIC discipline: callback-pointer statics in the dropped
   probes are exactly what PIC breaks silently; keep the
   ABS64 gate + -Werror; FB banner first so failure is
   visible.
3. v2 repack changes size fields — new surface vs Gate 1's
   byte-identical layout; first flash from recovery with
   the stock image one dd away (same as Gate 1).
4. Three different "page sizes" (2048 / 4096 / 0x4000) are
   already correctly separated in the sources — do not let
   an edit "unify" them.
5. Ramoops zones must sit strictly inside enumerated DRAM
   banks — dl_main writes the prz signature before any
   validation; a carve-out address aborts (visible via
   dl_exception ESR/FAR on the FB console).
6. A73 boot CPU propagates kernel-side (A5XELTE topology
   patches, SweetCPU), not loader-side — a first XNU hang
   is not automatically a loader bug; the entry marker +
   FB console separate the two.

## Smoke-test ladder before real XNU

(a) Loader + dummy payload whose "kernel" is a small
FB-pattern stub: validates /chosen discovery, segment copy,
ADT placement, and the jump with no XNU in the loop.
(b) Real A5XELTE + 0125 kernel. Success: entry marker
(XNUELTE1) read back from recovery and/or the Darwin banner
on the FB console reaching platform-expert init.
