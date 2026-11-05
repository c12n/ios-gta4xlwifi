# AI pack synthesis — Gate 0 walls (2026-11-05)

Wall protocol run (owner's instruction): Claude (Opus 5.5, Effort
Max), Gemini (3.1 Pro, High), DeepSeek (DeepThink + Search) were
each given the same two-wall brief in the browser. Every load-bearing
claim was then checked against ground truth: the live tablet dumps,
Samsung's own kernel sources, and — decisively — Samsung's base
device tree `arch/arm64/boot/dts/exynos/exynos9610.dts` (the 9610
base is reused for the 9611; fetched from LineageOS
android_kernel_samsung_gta4xl, branch lineage-23.2). Web agents did
not run any local tooling; all verification here is local.

## Wall 1 — downloading stock firmware

**Winner (verified working): `topjohnwu/samloader-rs`.**
Named independently by DeepSeek and Claude. v2.2.0 Linux binary:
`check-update -m SM-P610 -r XAC` returned the exact version string
`P610XXS7FYD1/P610OXM7FYD1/P610XXS7FYD1/P610XXS7FYD1` from
Samsung's current servers, and the 4.9 GB download is running with
it. It uses Smart Switch's newer no-IMEI endpoints.

Root causes of the original samloader failure (Claude, consistent
with everything observed locally):
- The `checkupdate` 403 is a **User-Agent filter** on the fota
  endpoint (nlscc sends no UA).
- The nonce crash is a **rotated key**: the legacy endpoint still
  answers, but nlscc's KEY_1 now decrypts the nonce to garbage.
  Our Content-Length: 0 patch for the 411 was correct but cannot
  fix the key. `ananjaser1211/samloader` carries the rotated keys
  (needs the device serial for downloads on Wi-Fi models);
  martinetd's fork still ships the old key (DeepSeek recommended
  it anyway — not followed).

**Falsified:** Gemini's headline answer — a Bifrost CLI jar
(`java -jar Bifrost.jar download …`) — **does not exist** (release
assets are GUI installers only; the URL 404s). Claude and DeepSeek
both correctly state Bifrost is GUI-only with no CLI/headless mode.

## Wall 2 — Exynos 9611 base device-tree facts

Ground truth = `exynos9610.dts` (Samsung). Scorecard:

| Fact | Truth (from the DTS) | Claude | DeepSeek | Gemini |
| --- | --- | --- | --- | --- |
| GIC compatible | `arm,cortex-a15-gic`, `arm,cortex-a9-gic` (GIC-400 hw) | ✅ exact | ~ (`arm,gic-400`) | ~ (`arm,gic-400`) |
| GIC reg | GICD 0x12301000/0x1000, GICC 0x12302000/**0x1000**, GICH 0x12304000/0x2000, GICV 0x12306000/0x2000 | ✅ exact | ✅ exact | ❌ GICC size 0x2000 |
| Timer | `arm,armv8-timer`, PPI 13/14/11/10 level-low, **clock-frequency 26000000** | ✅ exact | ✅ freq | ✅ freq |
| CNTFRQ | Bootloader leaves CNTFRQ_EL0 unprogrammed — hardcode 26 MHz in the ADT/shim | ✅ (also DeepSeek's note) | ✅ note | — |
| MCT | `samsung,exynos4210-mct`, reg 0x10040000/**0x800**, 12 IRQs | ✅ exact | ◐ hedged (honest) | ✅ compatible |
| UFS compatible | **`samsung,exynos-ufs`** (only match in Samsung's driver) | ✅ | ❌ `exynos7-ufs` | ❌ `exynos7-ufs` |
| UFS reg | HCI 0x13520000/0x200, vendor 0x13521100/0x200, **UniPro 0x13510000/0x8000**, protector 0x13530000/0x100; IRQ SPI 157 | ✅ exact | ❌ generic binding template (self-flagged) | — |
| UFS version | Not in DT; read VER register 0x13520008 on hardware (expect 2.1) | ✅ honest guess | ~ stated as fact | stated as fact |
| PSCI | `arm,psci`, method `smc`, CPU_SUSPEND 0xC4000001 / CPU_OFF 0x84000002 / CPU_ON 0xC4000003 | ✅ exact | ✅ exact | ✅ ids |
| PSCI reset | **SYSTEM_RESET/OFF/VERSION: no evidence; treat as unsupported.** Reset fallback: write 1 to PMU SWRESET @0x11860400 | ✅ (only Claude caught this) | — implied ok | ❌ implied SYSTEM_RESET works |

Also from Claude, corroborated by the live tree: RAM banks on the
device (0x80000000, 0xC0000000, 0xE1900000, 0x880000000 — the base
DTS memory nodes are generic placeholders the bootloader adjusts),
and a mainline simple-framebuffer reference at 0xCA000000
1200×2000 (from the gta4xl LTE mainline series — to verify on this
Wi-Fi unit at Gate 1/2).

XNU-specific notes carried forward to PORTING:
- ADT `timebase-frequency` must be **26000000** (XNU defaults to
  24 MHz → clock ~8.3% fast otherwise).
- GICv2: timer PPIs/IPIs arrive as IRQs via GICC_IAR, not FIQs —
  the port's interrupt plumbing must expect that.
- GICC is listed as 4 KiB in the DTS but the GIC-400 CPU interface
  is 8 KiB (GICC_DIR at +0x2000) — matters only for split-EOI mode.
- UFS downstream quirks to mirror: PRDT byte granularity, broken
  request-list clear, interrupt-aggregation skips; PHY calibration
  is 9610-specific (ufs-cal-9610).

## Verdict

Claude (Opus Max) was the most accurate — the only one to actually
verify against sources, and it caught the PSCI-reset trap. DeepSeek
co-found the winning tool and honestly flagged its one template.
Gemini was fastest and wrongest: fabricated headline tool, wrong
UFS compatible, wrong GICC size. **Rule reinforced: no pack claim
enters the hardware map until a local source confirms it.**
