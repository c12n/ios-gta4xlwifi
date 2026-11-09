#!/usr/bin/env python3
"""Build the Galaxy Tab S6 Lite (SM-P610, gta4xlwifi, Exynos 9611) ADT.

Layered on tools/mkadt.py exactly like mkadt_dreamlte.py is for the
Galaxy S8, with this board's verified facts (Gate 0 hardware map,
live device tree, shim v0.1 probe):
  - XNU RAM: 512 MiB inside the 2 GiB bank at 0x880000000 (the full
    bank panicked in kmem_range_init on the S8; same VA layout here)
  - GIC-400: GICD 0x12301000, GICC 0x12302000 (offsets under the
    arm-io ranges base 0x10000000); physical timer INTID 30
  - timer 26 MHz; CNTFRQ_EL0 is in fact programmed on this device
    (probe: 0x018CBA80), XNU still reads the property
  - CPUs: logical 0-3 = Cortex-A73 MPIDR 0x0-0x3 (S-Boot boots the
    A73 core 0 - unlike the S8, which boots an A53), logical 4-7 =
    Cortex-A53 MPIDR 0x100-0x103
  - S-Boot framebuffer 1200x2000 XRGB8888 at 0xCA000000
  - UFS: HCI 0x13520000, Exynos vendor block 0x13521100 (Gate 3)
The identity stays the donor's iPhone X (D22AP / iPhone10,3).
"""
import argparse
import os
from pathlib import Path

import adt
import mkadt

DRAM_BASE = 0x880000000
DRAM_SIZE = 0x20000000          # 512 MiB, per the S8 kmem_range_init lesson
FB_PHYS, FB_W, FB_H = 0xCA000000, 1200, 2000
TIMEBASE = 26000000


def set_prop(node, name, value):
    for i, (key, flags, _) in enumerate(node.props):
        if key == name:
            node.props[i] = (key, flags, value)
            return
    node.props.append((name, 0, value))


def child(node, name):
    for candidate in node.children:
        if candidate.prop('name') == mkadt.cstr(name):
            return candidate
    raise ValueError(f'missing donor ADT node {name}')


def cpu_node(logical):
    a73 = logical < 4
    mpidr = logical if a73 else 0x100 + (logical - 4)
    cluster = 0 if a73 else 1
    return [
        ('device_type', mkadt.cstr('cpu')),
        ('compatible', mkadt.cstr('arm,cortex-a73' if a73 else 'arm,cortex-a53') +
         mkadt.cstr('ARM,v8')),
        ('reg', mkadt.u32(mpidr)),
        ('cpu-id', mkadt.u32(logical)),
        ('cluster-id', mkadt.u32(cluster)),
        ('cluster-type', mkadt.u32(0)),
        ('die-cluster-id', mkadt.u32(cluster)),
        ('cluster-core-id', mkadt.u32(logical % 4)),
        ('l2-cache-id', mkadt.u32(cluster)),
        ('l3-cache-id', mkadt.u32(0)),
        ('state', mkadt.cstr('running' if logical == 0 else 'stopped')),
        ('timebase-frequency', mkadt.u32(TIMEBASE)),
        ('clock-frequency', mkadt.u32(2300000000 if a73 else 1700000000)),
        ('bus-frequency', mkadt.u32(100000000)),
        ('memory-frequency', mkadt.u32(2133000000)),
        ('peripheral-frequency', mkadt.u32(TIMEBASE)),
        ('fixed-frequency', mkadt.u32(TIMEBASE)),
    ]


def build(canvas=(FB_W, FB_H)):
    root = mkadt.build(seed=os.urandom(64), qemu=True)
    # The kernel's SweetPlatformExpert personality matches 'samsung,a5xelte'
    # (KernelConfigTables.cpp); without it IOKit panics "Unable to find driver
    # for this platform" (S8 boot 3). IONameMatch accepts any listed name.
    set_prop(root, 'compatible', mkadt.cstr('samsung,gta4xlwifi') +
             mkadt.cstr('samsung,a5xelte') + mkadt.cstr('samsung,exynos9611') +
             mkadt.cstr('AppleARM'))
    chosen = child(root, 'chosen')
    set_prop(chosen, 'dram-base', mkadt.u64(DRAM_BASE))
    set_prop(chosen, 'dram-size', mkadt.u64(DRAM_SIZE))
    set_prop(chosen, 'firmware-version', mkadt.cstr('gta4xlwifi-entry'))
    set_prop(chosen, 'system-firmware-version', mkadt.cstr('gta4xlwifi-entry'))
    cpus = child(root, 'cpus')
    cpu0 = child(cpus, 'cpu0')
    for key, value in cpu_node(0):
        if key != 'cpu-id':
            set_prop(cpu0, key, value)
    for logical in range(1, 8):
        cpus.children.append(mkadt.node(f'cpu{logical}', cpu_node(logical)))
    arm_io = child(root, 'arm-io')
    set_prop(arm_io, 'device_type', mkadt.cstr('gta4xlwifi-io'))
    set_prop(arm_io, 'compatible', mkadt.cstr('samsung,exynos9611-io') + mkadt.cstr('arm-io'))
    set_prop(arm_io, 'ranges', mkadt.u64(0, 0x10000000, 0xf0000000))
    arm_io.children = [n for n in arm_io.children if n.prop('name') == mkadt.cstr('wdt')]
    arm_io.children.append(mkadt.node('gic', [
        ('compatible', mkadt.cstr('arm,cortex-a15-gic')),
        ('interrupt-controller', mkadt.cstr('master')),
        # Non-secure physical timer (PPI 14): Samsung's DT says
        # "use-physical-timer"; the kernel (A5_USE_PHYS_TIMER) uses CNTP.
        ('virtual-timer-intid', mkadt.u32(30)),
        ('reg', mkadt.u64(0x2301000, 0x1000, 0x2302000, 0x1000)),
    ]))
    arm_io.children.append(mkadt.node('disp0', [
        ('device_type', mkadt.cstr('display-subsystem')),
        # AppleCLCD (SweetFramebuffer.cpp) matches 'samsung,a5xelte-display';
        # without it no main display exists and SpringBoard aborts (S8 boot 16).
        ('compatible', mkadt.cstr('samsung,gta4xlwifi-display') +
         mkadt.cstr('samsung,a5xelte-display')),
        # Must equal the size AppleCLCD reports. Our panel is the
        # framebuffer, so the native canvas is used from the start.
        ('canvas-width', mkadt.u32(canvas[0])),
        ('canvas-height', mkadt.u32(canvas[1])),
    ]))
    root.children = [n for n in root.children if n.prop('name') not in
                     (mkadt.cstr('sweet-fbcon'), mkadt.cstr('sweet-ufs'))]
    # pe_serial.c looks the console up by this name on the A5XELTE config.
    root.children.append(mkadt.node('a5xelte-fbcon', [
        ('reg', mkadt.u64(FB_PHYS, FB_W * FB_H * 4)),
        ('width', mkadt.u32(FB_W)),
        ('height', mkadt.u32(FB_H)),
        ('stride', mkadt.u32(FB_W * 4)),
    ]))
    # bsd/dev/sweet_ufs.c (A5XELTE config, EXYNOS_UFS): UFSHCI standard
    # registers, then the Exynos vendor HCI block. Gate 3.
    root.children.append(mkadt.node('gta4xlwifi-ufs', [
        ('reg', mkadt.u64(0x13520000, 0x200, 0x13521100, 0x200)),
    ]))
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--canvas', default=f'{FB_W}x{FB_H}',
                        help='display size presented to iOS, WxH')
    args = parser.parse_args()
    blob = adt.serialize(build(tuple(int(v) for v in args.canvas.split('x'))))
    args.output.write_bytes(blob)
    print(f'{args.output}: {len(blob)} bytes')
