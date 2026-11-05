# NOTES — engineering log

Every boot attempt, crash and decision, in order. Newest at the top
of each day's section. Log excerpts belong here, not in issues.

## 2026-11-05 — project start

- Project created: staged port (boot first) approved; full feature
  list (touch, Wi-Fi, charging/battery, GPU, all cores) is the
  long-term target — see PORTING.md gates.
- Timeframe updated by the owner later on 2026-11-05: **unlimited**
  (replacing the original two-week window). No deadline pressure;
  gates are cleared in order, however long each takes. Wi-Fi and
  Mali GPU remain research items in Gate 6, not guarantees.
- Bases chosen: ios-sweet (generic layer) + ios-galaxy-s8 (Exynos
  layer, pointed out by the project owner today — it reaches the
  lock screen on Exynos 8895, which materially improves the Exynos
  starting position vs. the Galaxy S7 precedent).
- Key facts carried in from the S8 port: GIC-400 (not v3), 4 KiB
  pages, own Exynos UFS driver, S-Boot framebuffer via DECON,
  loader in the BOOT partition, log via ramoops + USERDATA ring,
  Mali GPUs cannot run iOS Metal/AGX — CPU rendering is the plan.
- Repo skeleton written locally; public GitHub repo creation in
  progress (connector cannot create repos; browser route).
- Next: Gate 0 device dumps when the tablet is plugged into the
  owner's laptop. Nothing has been flashed; the tablet is untouched.

## Template for boot entries

### Boot NNN — YYYY-MM-DD HH:MM
- Build: <kernel commit / patch set / boot-args>
- Change vs last boot: <one thing>
- Result: <how far it got, verbatim log lines that matter>
- Next: <one next step>
