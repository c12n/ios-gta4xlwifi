# Credits

This port stands on the following projects. Code is only reused
where its licence allows; each reused file keeps its original
headers.

- **dipa-studio/ios-sweet** — the original iOS 16 port to the Redmi
  Note 10 Pro (XNU xnu-8796 + iPhone X 16.7.16 userland). The generic
  patch series, root-image builder and bring-up approach come from
  here. https://github.com/dipa-studio/ios-sweet
- **Floppikrob/ios-galaxy-s8** — iOS 16.7 on the Samsung Galaxy S8
  (Exynos 8895): S-Boot loader, Exynos UFS driver, GIC-400 / 4 KiB
  page setup, DECON framebuffer, SPEEDY/PMIC and HSI2C touch
  patterns. The Exynos layer of this port is modelled on it.
  https://github.com/Floppikrob/ios-galaxy-s8
- **orhunnx/ios-a5xelte** — the Galaxy A5 2016 (Exynos) port the S8
  project is based on.
- **hackiosx.dev** — documentation hub for this family of ports
  (how-it-works, porting guide, compatibility).
- **Apple's open-source releases** — XNU, IOHIDFamily, HFS and the
  other APSL/GPL components the kernel build is assembled from.
- **blacktop/darwin-xnu-build** — XNU build tooling used by the
  kernel CI.
- **LineageOS (gta4xl / gta4xlwifi device and kernel trees)** and
  **Samsung's published kernel source** — the hardware reference for
  this tablet: device tree, addresses, and how each chip is driven
  under Linux.
- **Mainline Linux** — Exynos, HSI2C and touch driver references.

iOS belongs to Apple and is not distributed here: download the IPSW
yourself.
