# Gate 2 design brief — XNU early boot (from the ios-sweet / ios-galaxy-s8 study, 2026-11-09)

Local sources: `~/workspace/ios-sweet`, `~/workspace/ios-galaxy-s8`.

## Headline

**The S8 repo is our direct template.** It is the ios-sweet design
already ported from Qualcomm/ABL to Samsung S-Boot / Exynos /
GICv2 / 4 KiB pages, and its deltas map almost 1:1 onto the
Exynos 9611. The `SWEET` machine config (16 KiB pages, GICv3
sysregs) is the wrong lineage: **the A5XELTE config + patch
series is ours**.

## How the loader works (summary)

- Host: `tools/mkpayload.py` builds a `SWEETXNU` v1 container
  (segments of a raw decompressed kernel, entry VA, ADT blob,
  608-byte cmdline; `phys_base` = the kernel's CONFIG_PHYSMAP_BASE,
  `mem_size` = flat 512 MiB). It is placed in the boot image's
  **ramdisk slot**; the shim binary takes the **kernel slot**.
- Device (`shim/dreamlte/{start.S,loader.c}` is the one to copy):
  PIC ARM64 Image header (S-Boot does not load at the header
  address - the build fails on any absolute relocation), entry at
  EL1 with MMU off and x0 = FDT, finds the payload through the
  FDT `/chosen` initrd properties, builds temp page tables only
  to copy fast, **zeroes the whole XNU RAM window** (S-Boot
  leaves dirty RAM; skipping this hangs XNU nondeterministically),
  copies Mach-O segments, places ADT in the gap below the window
  top and a rev-2 `boot_args` page after it, disables MMU/caches,
  branches to the kernel with **x0 = boot_args phys**.
- Extras in the S8 loader: dual-zone ramoops logging, a fixed
  8-byte XNU entry-marker slot (kernel writes `XNUELTE1` there -
  liveness proof even without a console), UFS wake probe,
  SPEEDY-bus PMIC/RTC (becomes an `s8rtc=` boot-arg), touch-rail
  power-up, DECON command-mode trigger unmask.

## Kernel

Not Apple's binary: **XNU xnu-8796 built from source**
(DEVELOPMENT, `kernel.development.a5xelte`) with ios-sweet
patches 0001-0032 + A5XELTE 0095-0123 + a generated per-board
patch (0124-dreamlte; ours will be **0125-gta4xlwifi**: FB
address, entry-marker address, boot MPIDR). Built on macOS
runners via the S8 repo's `xnu.yml` workflow shape. Hard
constraints: our A53/A73 are ARMv8.0 - **no 16 KiB granule, no
LSE atomics**; CI must scan the built kernel for LSE opcodes
(the S8 hit an `ldadd` undefined-instruction panic). The Apple
kernelcache from the IPSW is still needed for the D22AP ADT
donor and the Gate 3 rootfs.

Key patches for Gate 2: 0003 FB serial console, 0010 early FB
debug, 0016 SweetPlatformExpert, 0017 timer INTID from ADT
(timer/IPIs arrive as IRQs on GICv2, not FIQs), 0018 SweetCPU,
0097/0099/0100/0101 A5XELTE VA-size/timer/epoch/CPU-identity,
0114 GICv2 SGI INTID. S8 stability fixes to inherit: physmap
slide pinned to 0, `arm_vm_init` L3 budget including the FB
console mapping.

## ADT

Offline generator, never runtime: `mkadt.py` starts from the
genuine iPhone X D22AP ADT (from the 16.7.16 IPSW) and rewrites
the hardware description while keeping the iPhone10,3 identity.
Our layer `tools/mkadt_gta4xl.py` changes:

- root `compatible` includes **`samsung,a5xelte`** (the string
  the platform expert actually matches) + `samsung,gta4xlwifi`.
- `/chosen` dram-base/dram-size from our real map (below).
- `/cpus`: 8 nodes, MPIDR 0x0-0x3 (A73) and 0x100-0x103 (A53),
  `timebase-frequency = 26000000` (CNTFRQ is unprogrammed).
- `/arm-io/gic`: `arm,cortex-a15-gic`, GICD 0x12301000 /
  GICC 0x12302000 (as offsets under arm-io/ranges),
  `virtual-timer-intid = 30` (physical timer, S8 precedent).
- fbcon node named **`a5xelte-fbcon`**: reg 0xCA000000,
  size 1200x2000x4, width 1200, height 2000, stride 4800.
- UFS node defined now for Gate 3: 0x13520000/0x200 HCI +
  0x13521100/0x200 vendor.
- Delete donor `random`/`IOGPU`/`prng` (XNU panics on them);
  fresh seeds per build.

## RAM plan

- XNU window: 512 MiB inside the carve-out-free **0x880000000**
  bank (S8 lesson: the full 2 GiB bank panicked in
  kmem_range_init). Payload stays in the low bank (S-Boot loads
  the boot image kernel at 0x80080000).
- Open item: the live tree's exact per-bank sizes (Gate 0 dump
  recorded bank starts only; the DT/DTBO memory nodes are
  generic templates). Read the real `reg` values from
  /proc/device-tree next time the tablet is in recovery, then
  freeze dram values in mkadt.

## Boot image

Our stock boot is **header v2**, so the S8 packer does not
apply; reuse the Gate 1-proven splice: shim Image = kernel
slot, payload.bin = ramdisk slot, header/DTB byte-identical.
Display: DECON_F here is video mode (Gate 1 proved no trigger
poke is needed) - keep the S8 unmask only as a fallback.

## Open questions / risks, in solve order

1. ~~**Boot-CPU MPIDR unknown**~~ **SOLVED 2026-11-09** by the
   shim v0.1 probe (owner photo): **MPIDR = 0x0000 — S-Boot
   boots on A73 core 0 (unlike the S8's A53 0x100), at EL1**,
   and CNTFRQ_EL0 = 0x018CBA80 (26 MHz, programmed). ADT cpu0
   `reg` = 0x0 with `state` = running; the 0125 board patch's
   boot-MPIDR macro = 0x0.
2. **Ramoops zone**: Lineage recovery's reservation is unknown
   (the stock DT uses Samsung debug-snapshot instead, e.g.
   log_pstore at 0xF9D10000). Fallback plan: FB console only -
   Gate 1 proved that path. Extract from the recovery image
   before the first XNU attempt if cheap.
3. `/chosen` initrd values under a v2 header: log them on
   screen on the first loader run; fallback = stock header's
   ramdisk load address.
4. Timer: physical (INTID 30) first per S8; one-line mkadt
   switch if clock init stalls.
5. Watchdog node address unverified; harmless while
   `wdt=-1` is in the boot-args.
6. SMP (Gate 5, noted now): PSCI CPU_ON alone does not start
   Exynos cores on the S8; PMU CPU_CONFIGURATION registers
   (PMU base 0x11860000 on 9611) are written first, then PSCI.
   Verify the offset formula against
   `~/workspace/kernel-gta4xl` before use.

## Default first boot-args (from the S8 trial)

`debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam
-noprogress wdt=-1 wdt_test=no_user_checkin`

## Sequence

1. Shim v1 = dreamlte loader port + MPIDR/chosen logging.
2. CI-build kernel.development.a5xelte (+0125), LSE-scan.
3. mkadt_gta4xl from the extracted D22AP ADT.
4. mkpayload -> Gate 1 splice -> flash BOOT. Success =
   entry marker and/or Darwin banner + FB console reaching
   platform-expert init without panic.
