# tools provenance

- adt.py, mkadt.py: vendored from ios-galaxy-s8/tools (the
  A5XELTE fork of ios-sweet; mkadt.py differs between the two
  upstreams - this is the S8 fork's version, which
  mkadt_dreamlte.py and our mkadt_gta4xl.py layer on).
  ios-sweet is MIT (Copyright (c) 2026 dipa-studio); XNU-derived
  material is APSL 2.0. See the files' own headers.
- mkadt_gta4xl.py, mkdummy.py, im4p.py, fdt_dump.py: ours.
- The D22AP donor ADT (research/ipsw-x/d22ap.adt) is an Apple
  artifact extracted from the IPSW and is gitignored, never
  committed.
