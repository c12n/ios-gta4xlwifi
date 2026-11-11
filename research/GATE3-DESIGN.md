# Gate 3 design — storage (UFS) + rootfs to launchd

Written 2026-11-11, after Boot 002 (Gate 2 passed) and the
same-day diagnostic session. Gate 3 = XNU mounts an iOS root
filesystem from the tablet's UFS and execs /sbin/launchd.

## Where Boot 002 actually stopped (evidence, not guesses)

- Owner photos at ~1 and ~2 min: the framebuffer console's
  last line is `IOKit IOMD setownership ENABLED`. Nothing
  after; no panic, no "still waiting for root device".
- No SWEET UFS lines ever printed, although the driver
  printfs from its probe path (strings-verified in the
  built kernel, including our own message `SWEET UFS: no
  /gta4xlwifi-ufs node in the device tree`).
- The persistent console log (patch 0047) leaves a
  `SWEETLOG` header + 4 MiB ring in the LAST 4 MiB + 4 KiB
  of the root partition once that partition is known and
  writable. Read-back of userdata's last 8 MiB from
  recovery (2026-11-11): zero SWEET strings. The flusher
  never ran, so the UFS partition was never found/writable
  in Boot 002.
- Conclusion: execution stalled between IOKit init and the
  root-device path, BEFORE storage was ever reached. The
  stall, not storage, is Gate 3's first problem.

Recovery read-back channels are closed (checked 2026-11-11):
no /dev/mem (ENXIO), no /proc/kcore; pstore holds Android's
own ramoops region, not our zones. The framebuffer console
and the SWEETLOG-on-userdata ring (once storage works) are
the log channels. There is no physical serial out.

## Timer audit (the obvious suspect, cleared in its specifics)

- Our ADT carries virtual-timer-intid = 30 and patch 0125
  sets A5_USE_PHYS_TIMER 1 with A5XELTE_VTIMER_INTID
  redefined 27 -> 30. This EXACTLY mirrors the working
  dreamlte setup (mkadt_dreamlte.py: "Non-secure physical
  timer (PPI 14)... the kernel (A5_USE_PHYS_TIMER) uses
  CNTP", ADT value 30). INTID 30 = PPI 14 + 16, the
  non-secure physical timer. Not a mismatch.
- Still open: interrupt DELIVERY in general on this GIC-400
  (0x12301000/0x12302000) under our platform code. If the
  clock never ticks, the first timed sleep in the boot path
  hangs silently, which fits the symptom precisely. This is
  a hypothesis class, not a finding.

## What the kernel already has (strings/file audit)

- SWEET UFS host driver (0028): GPT partition by name,
  default `userdata` (0125: UFS_DEFAULT_PART), 4 KiB
  blocks, own DMA window; UFS writes (0030), read-write
  root (0031), DMA above 4 GiB (0034), faster path (0069).
- Built-in HFS (0026), unsealed root volume (0029),
  mockfs ramdisk root (0021/0022/0024) as a fallback root.
- SWEETLOG persistent console log (0047) + upstream reader
  tools (sweet-log-pull.sh in the S8 tree) for recovery
  read-back once the ring lands on userdata.
- ADT node /gta4xlwifi-ufs: HCI 0x13520000/0x200 + vendor
  0x13521100/0x200 (0125: UFS_ADT_NODE).

Unknown until a probe runs: Exynos 9611 UFS PHY/UniPro
bring-up vs the 8895 the driver was written against. The
PHY lives in the vendor window on 9610-family silicon; the
driver's init sequence is the test.

## Plan

### Step 1 — one diagnostic kernel build (offline, no tablet)
Add milestone kprintfs at the exact boundary Boot 002
died on: bsd_init entry, mountroot entry, UFS probe entry/
exit, plus a clock-alive check (a thread_call scheduled
5 s out that prints if it ever fires). One boot then
discriminates: no heartbeat + no bsd_init print = dead
clock/interrupts before BSD; bsd_init but no UFS entry =
root-config path; UFS entry but no exit = host init hang.
Change ONE variable per boot after that.

### Step 2 — rootfs image (offline, M2 mini)
Mirror the proven A5XELTE staging: extract the iPhone X
iOS 16.7.16 userland from the local IPSW rootfs (APFS,
mounted on macOS), stage it into a case-sensitive HFSX
image. Differences in our favour: userdata is
56,048,484,352 B (~52 GiB) vs A5's 11.25 GiB, so the FULL
userland fits with room to spare — no trimming pass.
Reserve the tail: make the HFS volume exactly
(partition size − 8 MiB) so SWEETLOG's last-4 MiB+4 KiB
area sits outside the volume, per 0047's layout.
Keep /sbin/launchd + SpringBoard ownership 0:0 and the
dyld cache ownership per the A5 staging notes.

### Step 3 — write userdata (DESTRUCTIVE, owner's call)
dd the image to /dev/block/by-name/userdata from recovery,
with the runbook's hash gates. This erases Android's data
partition. Stock backups cover boot/recovery/dtbo/vbmeta;
userdata is NOT backed up. Offer a one-time full userdata
backup to the MSI first (52 GiB over ADB, slow) and let
the owner decide. Nothing in this step happens without
his explicit go.

### Step 4 — Boot 003 and read the result
Expect, in order: SWEET UFS probe lines (host, LUN,
partition found), SWEET LOG start line, `hfs: mounted
<volume> on device ...`, then the first /sbin/launchd
exec attempt. After any boot, recovery can pull the full
console log from userdata's tail (SWEETLOG), ending the
photo-only era for kernel logs.

## Gate 3 pass criteria
Root volume mounted from UFS AND launchd exec attempted
(its own success/failure after exec is Gate 4 territory:
display + touch to the lock screen).
