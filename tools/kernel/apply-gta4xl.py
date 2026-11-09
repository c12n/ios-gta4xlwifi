#!/usr/bin/env python3
"""Apply the Galaxy Tab S6 Lite (gta4xlwifi, Exynos 9611) hardware
layer to an A5XELTE-patched xnu tree (prep-xnu-tree.sh output).

Modeled directly on ios-galaxy-s8's apply-dreamlte.py: the A5XELTE
machine config is reused unchanged; board facts are A5_* macros in
A5XELTE.h guarded by GTA4XL, with the A5 values kept for a
non-GTA4XL build. Every replacement asserts its expected match
count. Usage: apply-gta4xl.py XNU_TREE

Deltas vs the S8 layer, and why:
  - FB 0xCA000000 1200x2000 (DECON video mode; no frame-done wait,
    no present-lock edits - those were S8 tearing workarounds)
  - entry marker 0x8F007F000 / klog 0x8F0100000 (our ramoops zones
    in the top DRAM bank, matching shim/v1/loader.c)
  - boot MPIDR 0 (A73 boot core; the A5 default CPU map already
    matches our ADT, so SweetCPU.cpp needs no edits at all)
  - UFS node /gta4xlwifi-ufs, root partition name "userdata"
  - keys default OFF (ALIVE pinctrl banks unverified; Gate 4)
  - skipped entirely: S8 battery (SM5713 is Gate 6), S8 touch
    injection (ours is SPI Himax, Gate 4), s8rtc (no loader RTC
    source yet), SMP PMU block (Gate 5, PMU base 0x11860000)
"""
import sys
from pathlib import Path

tree = Path(sys.argv[1])


def edit(rel, pairs):
    path = tree / rel
    text = path.read_text()
    for old, new, count in pairs:
        found = text.count(old)
        if found != count:
            raise SystemExit(f'{rel}: expected {count}x {old!r}, found {found}')
        text = text.replace(old, new)
    path.write_text(text)
    print(f'edited {rel}')


edit('pexpert/pexpert/arm64/A5XELTE.h', [(
    '#define A5XELTE_VTIMER_INTID         27\n',
    '#define A5XELTE_VTIMER_INTID         27\n'
    '\n'
    '/*\n'
    ' * Samsung Galaxy Tab S6 Lite (SM-P610, gta4xlwifi, Exynos 9611) build\n'
    ' * of this port. Same Samsung S-Boot handoff, GIC-400 and 26 MHz timer\n'
    ' * as the A5/S8; the board facts that differ are below.\n'
    ' */\n'
    '#define GTA4XL                        1\n'
    '#if defined(GTA4XL)\n'
    '#define A5_FB_PHYS                    0xCA000000  /* exynos,fb_rmem */\n'
    '#define A5_FB_WIDTH                   1200\n'
    '#define A5_FB_HEIGHT                  2000\n'
    '#define A5_FB_STRIDE                  4800        /* bytes per row */\n'
    '#define A5_FB_2M_BLOCKS               5           /* 1200*2000*4 bytes */\n'
    '#define A5_ENTRY_MARKER_PHYS          0x8F007F000 /* slot in the loader\'s pstore text */\n'
    '#define A5_BOOT_MPIDR                 0x0         /* Cortex-A73 core 0 (probe-verified) */\n'
    '#define A5_KEYS_DEFAULT               0           /* ALIVE banks unverified */\n'
    '#define A5_TOUCH_DEFAULT              0           /* SPI Himax path absent */\n'
    '#define A5_KLOG_PHYS                  0x8F0100000 /* our ramoops pmsg zone */\n'
    '#define A5_KLOG_SIZE                  0x80000\n'
    '/* Samsung\'s 9611 kernel DT: arch timer "use-physical-timer". Use the\n'
    ' * non-secure physical timer, PPI 14 = INTID 30 (same as the S8). */\n'
    '#define A5_USE_PHYS_TIMER             1\n'
    '#undef A5XELTE_VTIMER_INTID\n'
    '#define A5XELTE_VTIMER_INTID         30\n'
    '#else\n'
    '#define A5_FB_PHYS                    0x67000000\n'
    '#define A5_FB_WIDTH                   1080\n'
    '#define A5_FB_HEIGHT                  1920\n'
    '#define A5_FB_STRIDE                  4320\n'
    '#define A5_FB_2M_BLOCKS               5\n'
    '#define A5_ENTRY_MARKER_PHYS          0x469ff100\n'
    '#define A5_BOOT_MPIDR                 0\n'
    '#define A5_KEYS_DEFAULT               1\n'
    '#define A5_TOUCH_DEFAULT              1\n'
    '#endif\n', 1)])

# Early assembly: entry/MMU/stage blocks (same macro-ization as the S8).
stage_rows = {'0x6705d0c0': 88, '0x6707ecc0': 120, '0x670a08c0': 152,
              '0x670c24c0': 184, '0x670e40c0': 216}
pairs = [('MOV64\tx10, 0x469ff100', 'MOV64\tx10, A5_ENTRY_MARKER_PHYS', 1)]
for addr, row in stage_rows.items():
    pairs.append((f'MOV64\tx10, {addr}',
                  f'MOV64\tx10, (A5_FB_PHYS + {row} * A5_FB_STRIDE + 240 * 4)', 1))
pairs += [
    ('mov\t\tx15, #4320', 'mov\t\tx15, #A5_FB_STRIDE', 2),
    ('mov\tx15, #4320', 'mov\tx15, #A5_FB_STRIDE', 3),
    ('MOV64\tx0, 0x67000000\n\tmov\t\tx4, x0\n\tmov\t\tx5, #5\n',
     'MOV64\tx0, A5_FB_PHYS\n\tmov\t\tx4, x0\n\tmov\t\tx5, #A5_FB_2M_BLOCKS\n', 1),
    ('MOV64\tx10, 0x67000000', 'MOV64\tx10, A5_FB_PHYS', 1),
    ('mov\t\tx13, #5\nLa5_fb_attr:', 'mov\t\tx13, #A5_FB_2M_BLOCKS\nLa5_fb_attr:', 1),
    ('MOV64\tx4, 0x67000000\n\tmov\tx5, #4320',
     'MOV64\tx4, A5_FB_PHYS\n\tmov\tx5, #A5_FB_STRIDE', 1),
    ('mov\tx13, #8640', 'mov\tx13, #(2 * A5_FB_STRIDE)', 1),
    ('/* Five 2 MiB blocks map the 1080x1920 scanout buffer VA=PA.',
     '/* A5_FB_2M_BLOCKS 2 MiB blocks map the scanout buffer VA=PA.', 1),
]
edit('osfmk/arm64/start.s', pairs)

edit('osfmk/arm64/sweet_early.c', [
    ('#define A5_FB ((volatile uint32_t *)(uintptr_t)0x67000000)\n#define A5_STRIDE 1080u\n',
     '#define A5_FB ((volatile uint32_t *)(uintptr_t)A5_FB_PHYS)\n#define A5_STRIDE (A5_FB_STRIDE / 4u)\n', 1),
    ('#define A5_COLS (1080u / A5_COL_WIDTH)', '#define A5_COLS (A5_FB_WIDTH / A5_COL_WIDTH)', 1),
    ('(1920u / A5_ROW_HEIGHT)', '(A5_FB_HEIGHT / A5_ROW_HEIGHT)', 1),
    ('for (unsigned int x = 0; x < A5_STRIDE; x++) {', 'for (unsigned int x = 0; x < A5_FB_WIDTH; x++) {', 1),
])

edit('iokit/Kernel/arm/SweetFramebuffer.cpp', [
    ('#include <pexpert/pexpert.h>\n',
     '#include <pexpert/pexpert.h>\n#include <pexpert/arm64/board_config.h>\n', 1),
    ('\tfPhys = 0x67000000ULL;\n\tfWidth = 1080;\n\tfHeight = 1920;\n\tfRowBytes = 4320;\n',
     '\tfPhys = A5_FB_PHYS;\n\tfWidth = A5_FB_WIDTH;\n\tfHeight = A5_FB_HEIGHT;\n\tfRowBytes = A5_FB_STRIDE;\n', 1),
    ('#if !defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '\tif (!native && fWidth <= SWEET_FB_LOGICAL_W && fHeight <= SWEET_FB_LOGICAL_H) {\n',
     '#if defined(GTA4XL)\n'
     '\tif (!native) {\n'
     '\t\tfLogicalW = SWEET_FB_LOGICAL_W;\n'
     '\t\tfLogicalH = SWEET_FB_LOGICAL_H;\n'
     '\t}\n'
     '#elif !defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '\tif (!native && fWidth <= SWEET_FB_LOGICAL_W && fHeight <= SWEET_FB_LOGICAL_H) {\n', 1),
])

edit('pexpert/arm/pe_serial.c', [
    ('static uint32_t fbcon_cols, fbcon_rows, fbcon_col, fbcon_row;\n',
     'static uint32_t fbcon_cols, fbcon_rows, fbcon_col, fbcon_row;\n'
     '\n'
     '#if defined(GTA4XL)\n'
     '/*\n'
     ' * Copy of the console in our ramoops pmsg zone (top DRAM bank), in\n'
     ' * persistent_ram format (sig "DBGC", start, size, ring data),\n'
     ' * appended to the loader\'s text there. Read back with dd from\n'
     ' * Lineage recovery after a forced reboot.\n'
     ' */\n'
     '#define KLOG_CAP        (A5_KLOG_SIZE - 12)\n'
     'static volatile uint32_t *klog_hdr;\n'
     'static volatile uint8_t *klog_data;\n'
     'static uint32_t klog_start, klog_size;\n'
     'static void klog_putc(uint8_t c);\n'
     '\n'
     'static void\n'
     'klog_init(void)\n'
     '{\n'
     '\tklog_hdr = (volatile uint32_t *)ml_io_map(A5_KLOG_PHYS, A5_KLOG_SIZE);\n'
     '\tif (klog_hdr == NULL) {\n'
     '\t\treturn;\n'
     '\t}\n'
     '\tklog_data = (volatile uint8_t *)(klog_hdr + 3);\n'
     '\t/* Continue after the loader\'s text if its header is sane. */\n'
     '\tif (klog_hdr[0] == 0x43474244u && klog_hdr[1] == klog_hdr[2] &&\n'
     '\t    klog_hdr[2] < KLOG_CAP - 0x10000) {\n'
     '\t\tklog_start = klog_size = klog_hdr[2];\n'
     '\t} else {\n'
     '\t\tklog_hdr[0] = 0x43474244u;\n'
     '\t\tklog_start = klog_size = 0;\n'
     '\t}\n'
     '\tconst char *banner = "\\n--- XNU console ---\\n";\n'
     '\tfor (; *banner; banner++) {\n'
     '\t\tklog_putc((uint8_t)*banner);\n'
     '\t}\n'
     '}\n'
     '\n'
     'static void\n'
     'klog_putc(uint8_t c)\n'
     '{\n'
     '\tif (klog_data == NULL) {\n'
     '\t\treturn;\n'
     '\t}\n'
     '\tklog_data[klog_start] = c;\n'
     '\tklog_start = (klog_start + 1) % KLOG_CAP;\n'
     '\tif (klog_size < KLOG_CAP) {\n'
     '\t\tklog_size++;\n'
     '\t}\n'
     '\tklog_hdr[1] = klog_start;\n'
     '\tklog_hdr[2] = klog_size;\n'
     '}\n'
     '#endif\n', 1),
    ('fbcon_transmit_data(uint8_t c)\n{\n',
     'fbcon_transmit_data(uint8_t c)\n{\n'
     '#if defined(GTA4XL)\n'
     '\tklog_putc(c);\n'
     '#endif\n', 1),
    ('\tfbcon_base = (volatile uint32_t *)ml_io_map_wcomb(reg[0], reg[1]);\n',
     '\tfbcon_base = (volatile uint32_t *)ml_io_map_wcomb(reg[0], reg[1]);\n'
     '#if defined(GTA4XL)\n'
     '\tklog_init();\n'
     '#endif\n', 1),
])

# Physmap slide pinned to 0 + L3 budget for the FB console (S8 boots 3-7,
# 14, 15 root cause; the mechanism is board-independent).
edit('osfmk/arm64/arm_vm_init.c', [
    ('\tuint64_t physmap_slide = early_random() & ARM64_PHYSMAP_SLIDE_MASK & ~((uint64_t)PAGE_MASK);\n',
     '#if defined(GTA4XL)\n'
     '\tuint64_t physmap_slide = 0;\n'
     '#else\n'
     '\tuint64_t physmap_slide = early_random() & ARM64_PHYSMAP_SLIDE_MASK & ~((uint64_t)PAGE_MASK);\n'
     '#endif\n', 1),
    ('\tva_l1_end += round_page(args->Video.v_height * args->Video.v_rowBytes);\n',
     '\tva_l1_end += round_page(args->Video.v_height * args->Video.v_rowBytes);\n'
     '#if defined(GTA4XL)\n'
     '\tva_l1_end += round_page((vm_size_t)A5_FB_STRIDE * A5_FB_HEIGHT) + (64ULL << 20);\n'
     '#endif\n', 1),
    ('\tphysmap_base += physmap_slide;\n',
     '\tphysmap_base += physmap_slide;\n'
     '#if defined(GTA4XL) && !XNU_MONITOR\n'
     '\tphysmap_base = ROUND_TWIG(physmap_base);\n'
     '#endif\n', 1),
])

edit('osfmk/vm/vm_resident.c', [
    ('\tpmap_startup(&virtual_space_start, &virtual_space_end);\n',
     '#if defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '\tkprintf("A5 vm: vm_page_bootstrap -> pmap_startup\\n");\n'
     '#endif\n'
     '\tpmap_startup(&virtual_space_start, &virtual_space_end);\n', 1),
    ('\tvm_pages = (vm_page_t) pmap_steal_freeable_memory(npages * sizeof *vm_pages);\n',
     '\tvm_pages = (vm_page_t) pmap_steal_freeable_memory(npages * sizeof *vm_pages);\n'
     '#if defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '\tkprintf("A5 vm: npages=%u vm_pages=%p mem_sz=%#llx\\n", npages, vm_pages, (unsigned long long)mem_sz);\n'
     '#endif\n', 1),
    ('\t\tif (!pmap_next_page(&phys_page)) {\n\t\t\tbreak;\n\t\t}\n\n\t\tif (phys_page < max_valid_low_ppnum) {\n',
     '\t\tif (!pmap_next_page(&phys_page)) {\n\t\t\tbreak;\n\t\t}\n'
     '#if defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '\t\tif ((i & 0x7fff) == 0) {\n'
     '\t\t\tkprintf("A5 vm: page %u ppn %#x\\n", i, phys_page);\n'
     '\t\t}\n'
     '#endif\n'
     '\n\t\tif (phys_page < max_valid_low_ppnum) {\n', 1),
    ('\tvm_page_pages = vm_pages_count; /* used to report to user space */\n',
     '\tvm_page_pages = vm_pages_count; /* used to report to user space */\n'
     '#if defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '\tkprintf("A5 vm: %u pages initialized, releasing\\n", vm_pages_count);\n'
     '#endif\n', 1),
])

# ---- Exynos UFS: the SWEET driver with the Exynos quirks (Gate 3) ----
edit('bsd/dev/sweet_ufs.c', [
    ('#if defined(ARM64_BOARD_CONFIG_SWEET)\n#include <sys/param.h>\n',
     '#if defined(ARM64_BOARD_CONFIG_SWEET) || defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '#include <sys/param.h>\n', 1),
    ('#define CAP_64AS        (1u << 24)              /* 64-bit DMA addressing */\n',
     '#define CAP_64AS        (1u << 24)              /* 64-bit DMA addressing */\n'
     '\n'
     '#if defined(ARM64_BOARD_CONFIG_A5XELTE)\n'
     '/*\n'
     ' * Exynos 9611 host, per the Samsung downstream driver and the S8\n'
     ' * loader-probe findings on the 8895 (same controller lineage):\n'
     ' * UTRD offsets and lengths are in bytes, PRDT entries are 16 bytes\n'
     ' * and cover at most 4 KiB, each SCSI slot needs its\n'
     ' * HCI_UTRL_NEXUS_TYPE bit, the standard HCE register reads 0 while\n'
     ' * the host runs and UTRLCLR is inverted. S-Boot leaves the device\n'
     ' * stopped: START STOP UNIT (ACTIVE) to the Device W-LUN wakes it.\n'
     ' * The 9611-specific PHY calibration lives in the vendor block the\n'
     ' * ADT node names; S-Boot has already run it.\n'
     ' */\n'
     '#define EXYNOS_UFS              1\n'
     '#define VS_UTRL_NEXUS_TYPE      0x40\n'
     '#define UFS_WLUN_DEVICE         0xd0\n'
     '#define UFS_ADT_NODE            "/gta4xlwifi-ufs"\n'
     '#define UFS_DEFAULT_PART        "userdata"\n'
     '#define PRDT_BYTES(field)       (field)\n'
     '#else\n'
     '#define UFS_ADT_NODE            "/sweet-ufs"\n'
     '#define UFS_DEFAULT_PART        "userdata"\n'
     '#define PRDT_BYTES(field)       ((field) * 16u)\n'
     '#endif\n', 1),
    ('#define PRDT_CHUNK      (256u << 10)            /* PRDT byte count field: 18 bits */\n',
     '#if defined(EXYNOS_UFS)\n'
     '#define PRDT_CHUNK      4096u                   /* HCI_TXPRDT_ENTRY_SIZE 12 */\n'
     '#else\n'
     '#define PRDT_CHUNK      (256u << 10)            /* PRDT byte count field: 18 bits */\n'
     '#endif\n', 1),
    ('\tvm_offset_t regs;\n',
     '\tvm_offset_t regs;\n\tvm_offset_t vs_regs;                    /* Exynos vendor HCI registers */\n', 1),
    ('\tutrd->resp = (512u / 4) << 16 | (512u / 4);\n',
     '#if defined(EXYNOS_UFS)\n'
     '\tutrd->resp = 512u << 16 | 512u;\n'
     '#else\n'
     '\tutrd->resp = (512u / 4) << 16 | (512u / 4);\n'
     '#endif\n', 1),
    ('\t\tutrd->prdt = (1024u / 4) << 16 | n;\n',
     '#if defined(EXYNOS_UFS)\n'
     '\t\tutrd->prdt = 1024u << 16 | (n * (uint32_t)sizeof(ucd->prdt[0]));\n'
     '#else\n'
     '\t\tutrd->prdt = (1024u / 4) << 16 | n;\n'
     '#endif\n', 1),
    ('\t\t\t    (utrd->prdt & 0xffff) * sizeof(ucd->prdt[0]));\n',
     '\t\t\t    PRDT_BYTES(utrd->prdt & 0xffff));\n', 1),
    ('\tufs_wr(REG_UTRLDBR, 1);\n',
     '#if defined(EXYNOS_UFS)\n'
     '\t*(volatile uint32_t *)(su.vs_regs + VS_UTRL_NEXUS_TYPE) |= 1;  /* slot 0: SCSI */\n'
     '#endif\n'
     '\tufs_wr(REG_UTRLDBR, 1);\n', 1),
    ('\t\t\tufs_wr(REG_UTRLCLR, ~1u);\n',
     '#if !defined(EXYNOS_UFS)\n'
     '\t\t\tufs_wr(REG_UTRLCLR, ~1u);\n'
     '#endif\n', 1),
    ('\tif (!(hce & 1) || !(hcs & HCS_DP) || !(hcs & HCS_UTRLRDY)) {\n',
     '#if defined(EXYNOS_UFS)\n'
     '\t(void)hce;\n'
     '\tif (!(hcs & HCS_DP) || !(hcs & HCS_UTRLRDY)) {\n'
     '#else\n'
     '\tif (!(hce & 1) || !(hcs & HCS_DP) || !(hcs & HCS_UTRLRDY)) {\n'
     '#endif\n', 1),
    ('\tchar want[64] = "userdata";\n', '\tchar want[64] = UFS_DEFAULT_PART;\n', 1),
    ('\tif (SecureDTLookupEntry(NULL, "/sweet-ufs", &node) != kSuccess ||\n'
     '\t    SecureDTGetProperty(node, "reg", (void const **)&reg, &size) != kSuccess ||\n'
     '\t    size < 2 * sizeof(uintptr_t)) {\n'
     '\t\tprintf("SWEET UFS: no /sweet-ufs node in the device tree\\n");\n',
     '\tif (SecureDTLookupEntry(NULL, UFS_ADT_NODE, &node) != kSuccess ||\n'
     '\t    SecureDTGetProperty(node, "reg", (void const **)&reg, &size) != kSuccess ||\n'
     '#if defined(EXYNOS_UFS)\n'
     '\t    size < 4 * sizeof(uintptr_t)) {\n'
     '#else\n'
     '\t    size < 2 * sizeof(uintptr_t)) {\n'
     '#endif\n'
     '\t\tprintf("SWEET UFS: no " UFS_ADT_NODE " node in the device tree\\n");\n', 1),
    ('\tsu.regs = ml_io_map(reg[0], reg[1]);\n',
     '\tsu.regs = ml_io_map(reg[0], reg[1]);\n'
     '#if defined(EXYNOS_UFS)\n'
     '\tsu.vs_regs = ml_io_map(reg[2], reg[3]);\n'
     '#endif\n', 1),
    ('\terror = ufs_take_over_host();\n',
     '\terror = ufs_take_over_host();\n'
     '#if defined(EXYNOS_UFS)\n'
     '\tif (!error) {\n'
     '\t\tstatic const uint8_t ssu_active[6] = { 0x1b, 0, 0, 0, 0x10, 0 };\n'
     '\t\tsu.lun = UFS_WLUN_DEVICE;\n'
     '\t\terror = ufs_scsi(ssu_active, sizeof(ssu_active), 0, false);\n'
     '\t\tsu.lun = 0;\n'
     '\t\tprintf("SWEET UFS: START STOP UNIT (ACTIVE) to the device W-LUN: %d\\n", error);\n'
     '\t}\n'
     '#endif\n', 1),
    ('\tsweet_sample_start();\n\t/* Input drivers (HID services in iokit/Kernel/arm/hid/SweetHID.cpp). */\n'
     '\tsweet_keys_init();\n\tsweet_touch_init();\n\tsweet_usb_probe();\n',
     '\tsweet_sample_start();\n'
     '#if defined(ARM64_BOARD_CONFIG_SWEET)\n'
     '\t/* Input drivers (HID services in iokit/Kernel/arm/hid/SweetHID.cpp). */\n'
     '\tsweet_keys_init();\n\tsweet_touch_init();\n\tsweet_usb_probe();\n'
     '#endif\n', 1),
])

edit('bsd/dev/sweet_sample.c', [
    ('#if defined(ARM64_BOARD_CONFIG_SWEET)\n/*\n * SWEET process sampler',
     '#if defined(ARM64_BOARD_CONFIG_SWEET) || defined(ARM64_BOARD_CONFIG_A5XELTE)\n/*\n * SWEET process sampler', 1),
])

edit('iokit/bsddev/IOKitBSDInit.cpp', [
    ('#if defined(ARM64_BOARD_CONFIG_SWEET)\n//\n//\tSWEET: root on a GPT partition of the internal UFS (bsd/dev/sweet_ufs.c)\n',
     '#if defined(ARM64_BOARD_CONFIG_SWEET) || defined(ARM64_BOARD_CONFIG_A5XELTE)\n//\n'
     '//\tSWEET / gta4xlwifi: root on a GPT partition of the internal UFS (bsd/dev/sweet_ufs.c)\n', 1),
])

edit('osfmk/console/serial_console.c', [
    ('#if defined(ARM64_BOARD_CONFIG_SWEET)\nextern void sweet_log_append',
     '#if defined(ARM64_BOARD_CONFIG_SWEET) || defined(ARM64_BOARD_CONFIG_A5XELTE)\nextern void sweet_log_append', 1),
    ('#if defined(ARM64_BOARD_CONFIG_SWEET)\n\tsweet_log_append(c, size);',
     '#if defined(ARM64_BOARD_CONFIG_SWEET) || defined(ARM64_BOARD_CONFIG_A5XELTE)\n\tsweet_log_append(c, size);', 1),
])

# Physical instead of virtual EL1 timer (A5_USE_PHYS_TIMER).
edit('osfmk/arm64/machine_routines.c', [
    ('\t\t__builtin_arm_wsr64("CNTV_TVAL_EL0", (uint64_t)dec_value);\n',
     '#if defined(A5_USE_PHYS_TIMER)\n'
     '\t\t__builtin_arm_wsr64("CNTP_TVAL_EL0", (uint64_t)dec_value);\n'
     '#else\n'
     '\t\t__builtin_arm_wsr64("CNTV_TVAL_EL0", (uint64_t)dec_value);\n'
     '#endif\n', 1),
    ('\t\twide_val = __builtin_arm_rsr64("CNTV_TVAL_EL0");\n',
     '#if defined(A5_USE_PHYS_TIMER)\n'
     '\t\twide_val = __builtin_arm_rsr64("CNTP_TVAL_EL0");\n'
     '#else\n'
     '\t\twide_val = __builtin_arm_rsr64("CNTV_TVAL_EL0");\n'
     '#endif\n', 1),
    ('\tuint64_t cntv_ctl = __builtin_arm_rsr64("CNTV_CTL_EL0");\n',
     '#if defined(A5_USE_PHYS_TIMER)\n'
     '\tuint64_t cntv_ctl = __builtin_arm_rsr64("CNTP_CTL_EL0");\n'
     '#else\n'
     '\tuint64_t cntv_ctl = __builtin_arm_rsr64("CNTV_CTL_EL0");\n'
     '#endif\n', 1),
    ('\t__builtin_arm_wsr64("CNTV_CTL_EL0", cntvctl);\n'
     '\t/* disable the physical timer as a precaution, as its registers reset to architecturally unknown values */\n'
     '\t__builtin_arm_wsr64("CNTP_CTL_EL0", CNTP_CTL_EL0_IMASKED);\n',
     '#if defined(A5_USE_PHYS_TIMER)\n'
     '\t__builtin_arm_wsr64("CNTP_CTL_EL0", cntvctl);   /* same ENABLE bit */\n'
     '\t__builtin_arm_wsr64("CNTV_CTL_EL0", CNTV_CTL_EL0_IMASKED);\n'
     '#else\n'
     '\t__builtin_arm_wsr64("CNTV_CTL_EL0", cntvctl);\n'
     '\t/* disable the physical timer as a precaution, as its registers reset to architecturally unknown values */\n'
     '\t__builtin_arm_wsr64("CNTP_CTL_EL0", CNTP_CTL_EL0_IMASKED);\n'
     '#endif\n', 1),
])

edit('pexpert/arm/pe_fiq.c', [
    ('\t    a5_gic_read32(a5_gicd_base, 0x080) | (1U << 27) | (1U << 1));\n',
     '\t    a5_gic_read32(a5_gicd_base, 0x080) | (1U << A5XELTE_VTIMER_INTID) | (1U << 1));\n', 1),
    ('\ta5_gic_write32(a5_gicd_base, 0x100, (1U << 27) | (1U << 1));\n',
     '\ta5_gic_write32(a5_gicd_base, 0x100, (1U << A5XELTE_VTIMER_INTID) | (1U << 1));\n', 1),
])

# IOKit platform expert / display personalities: also match our names.
edit('iokit/KernelConfigTables.cpp', [
    ("    \"     'IONameMatch'     = 'samsung,a5xelte-display';\"\n",
     "    \"     'IONameMatch'     = ('samsung,a5xelte-display', 'samsung,gta4xlwifi-display');\"\n", 1),
    ("    \"     'IONameMatch'     = 'samsung,a5xelte';\"\n",
     "    \"     'IONameMatch'     = ('samsung,a5xelte', 'samsung,gta4xlwifi');\"\n", 1),
])

# A5 touch probe maps Exynos7580 I2C/GPIO blocks: keep it off here.
edit('bsd/dev/a5xelte_touch.c', [
    ('#include <pexpert/pexpert.h>\n',
     '#include <pexpert/pexpert.h>\n#include <pexpert/arm64/board_config.h>\n', 1),
    ('a5xelte_touch_probe(void)\n{\n\tint enabled = 1;\n',
     'a5xelte_touch_probe(void)\n{\n\tint enabled = A5_TOUCH_DEFAULT; /* A5 touch: off on gta4xlwifi */\n', 1),
])
