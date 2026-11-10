# Gate 2 tablet session — runbook (mistake-proofing)

Written 2026-11-10 at the owner's direction ("make no mistakes").
Every step has a verify gate. A failed gate means STOP, not retry-and-hope.
Only ONE partition is ever written in this session:
`/dev/block/by-name/boot` (= sda12, 59 MiB). Nothing else. No vbmeta,
no recovery, no other partition, under any circumstances.

## Verified facts (re-checked locally 2026-11-10)

| Item | Size | SHA-256 |
|---|---|---|
| boot-loader-smoke.img | 192,512 B (47 × 4096) | 5a70c55da39be15bf09c0358a3bc1c8b14e2cff4c98423f6c9a15569c476d9c6 |
| boot-loader-xnu.img | 16,646,144 B (4064 × 4096) | 9003b7522fc3443d82bc8d2fafd61cad8f92672739116ed6d56cbb547c31f5e2 |
| stock boot backup (restore) | 61,865,984 B = full partition | 694fd5da12776f2ae5e1cf245d2b00fe36889bb9a2e37d04caf825224c0cdf6a |

- Both images re-parsed 2026-11-10: `ANDROID!` magic, header v2,
  page 2048, kernel_size 46,192 (the loader, identical in both),
  ramdisk_size 5,384 (smoke payload) / 16,458,624 (XNU payload),
  `SWEETXNU` magic present at the ramdisk offset in both.
- The stock backup on the MSI (`gate1-backup\boot.img`) is byte-identical
  to the local stock firmware boot.img (same hash) — two restore sources.
- Staged copies on the MSI were hash-verified in place 2026-11-09 19:37.
  They are RE-verified on the tablet in /tmp before any dd (steps B1/D1),
  so a staging error cannot reach the partition.
- Proven flash path (Gate 1, twice): push to /tmp → sha256 in /tmp →
  dd to /dev/block/by-name/boot → read-back sha256 → adb reboot.

## The one subtle trap

Both new images are SMALLER than the 59 MiB partition. A whole-partition
read-back hash will therefore NEVER match the image hash — the tail is
stale bytes from the previous image, which S-Boot ignores (it honours the
header's kernel/ramdisk sizes). Read-back verification must compare only
the first N blocks: 47 for smoke, 4064 for XNU. The stock backup IS
full-partition size, so its restore read-back compares the whole
partition. Do not mix these two up mid-session.

## Pre-flight (before touching the tablet)

1. MSI awake; `adb` reachable through it.
2. Tablet battery ≥ 50%.
3. Owner present for the whole session. Any step the owner has not
   agreed to does not happen.

## Step A — get to Lineage recovery

Tablet currently runs shim v0.1 (colour bands + hex readouts, no ADB).

1. Force off: hold Power + Vol Down ~10 s until the screen goes black.
2. Immediately Power + Vol Up; release Power at the Samsung logo;
   keep holding Vol Up until the Lineage recovery menu appears.
3. If ADB reports `unauthorized`, the owner taps Allow on the tablet
   prompt (or Advanced → Enable ADB).
4. Gate: `adb shell id` returns uid=0. No uid=0, no flashing.

## Step B — smoke test (loader + dummy stub)

1. Push `gate1\boot-loader-smoke.img` to `/tmp/smoke.img`.
   Gate: `sha256sum /tmp/smoke.img` =
   5a70c55da39be15bf09c0358a3bc1c8b14e2cff4c98423f6c9a15569c476d9c6.
   Mismatch → delete, re-push, re-check. Never flash an unverified file.
2. `dd if=/tmp/smoke.img of=/dev/block/by-name/boot bs=4096`
   Gate: dd reports 192,512 bytes written.
3. Read-back (prefix only, see trap above):
   `dd if=/dev/block/by-name/boot bs=4096 count=47 | sha256sum`
   Gate: equals the smoke hash. Mismatch → re-dd once, re-check;
   still wrong → STOP, restore stock, diagnose offline.
4. `adb reboot`. Expected: loader console text, then the stub's
   cyan/magenta checkerboard. Owner photographs the screen.
5. Return to recovery (Step A) before Step D.

## Step C — marker read-back (optional, do not improvise)

From recovery, try reading the entry marker at phys 0x8F007F000 via
/dev/mem (`DUMMYOK!` expected after a good smoke boot) and the ramoops
zones at 0x8F0000000 / 0x8F0100000. This route is unverified; if /dev/mem
is blocked, the photo from B4 is sufficient evidence. Do not install
anything or change recovery to force this.

## Step D — XNU boot test

1. Push `gate1\boot-loader-xnu.img` to `/tmp/xnu.img`.
   Gate: `sha256sum /tmp/xnu.img` =
   9003b7522fc3443d82bc8d2fafd61cad8f92672739116ed6d56cbb547c31f5e2.
2. `dd if=/tmp/xnu.img of=/dev/block/by-name/boot bs=4096`
   Gate: dd reports 16,646,144 bytes written.
3. Read-back (prefix only):
   `dd if=/dev/block/by-name/boot bs=4096 count=4064 | sha256sum`
   Gate: equals the XNU hash.
4. `adb reboot`. Owner photographs whatever appears — loader text,
   Darwin banner, or a panic screen are all valid data. Success =
   platform-expert init reached without panic; the `XNUELTE1` marker
   and the pmsg klog at phys 0x8F0100000 are read back afterwards
   from recovery if the /dev/mem route works.
5. Log the outcome in NOTES.md (build / one change / verbatim result /
   next step) and in the goal tracker, whatever the result.

## Restore (available at any point, owner's call)

From recovery: push `gate1-backup\boot.img` to `/tmp/stock-boot.img`,
verify sha256 = 694fd5da…, then
`dd if=/tmp/stock-boot.img of=/dev/block/by-name/boot bs=4096` and
read back the FULL partition hash — it must equal 694fd5da… exactly,
because the stock image fills the partition. Fallback: reflash the
verified stock firmware with samloader-rs.

## Abort rules

- Any hash mismatch that survives one re-transfer → session stops,
  stock restored if BOOT was written, diagnosis happens offline.
- Any doubt about which partition a path points to → stop and check
  (`ls -l /dev/block/by-name/`), never guess.
- Nothing is flashed while the owner is away or unreachable.
