# shim/v1 provenance

The v1 loader is a port of the Galaxy S8 (dreamlte) XNU loader
from https://github.com/Floppikrob/ios-galaxy-s8, itself built
on https://github.com/dipa-studio/ios-sweet.

- start.S, loader.c: GPL-2.0-only (SPDX headers preserved in
  the files), Copyright the ios-galaxy-s8 authors.
- fdt.c, fdt.h, font.h: from ios-sweet (MIT, Copyright
  (c) 2026 dipa-studio) via ios-galaxy-s8.
- Adaptations for gta4xlwifi (Exynos 9611) are by c12n Apps;
  see research/GATE2-LOADER-PORT.md for the delta list.

Upstream probe files (pmic/smp/ufs/touch/display) were NOT
vendored; they return per-gate as noted in the port spec.
