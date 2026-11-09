/* SPDX-License-Identifier: GPL-2.0-only
 * Galaxy Tab S6 Lite (SM-P610, Exynos 9611) XNU loader.
 *
 * Ported from the Galaxy S8 (dreamlte) loader in ios-galaxy-s8
 * (see UPSTREAM.md). Board deltas are listed in
 * research/GATE2-LOADER-PORT.md; in short: framebuffer at
 * 0xCA000000 (1200x2000, DECON video mode - no trigger unmask),
 * ramoops zones relocated into the top DRAM bank above the XNU
 * window, low-RAM bound from the live device tree, all S8
 * hardware probes (PMIC/UFS/touch/battery/display/SMP) dropped
 * for Gate 2, and a hardcoded initrd fallback because whether
 * S-Boot's v2-header flow populates /chosen is unverified.
 *
 * S-Boot hands us the BOOT ramdisk as /chosen/linux,initrd-{start,end};
 * it holds a tools/mkpayload.py "SWEETXNU" v1 container (Mach-O
 * segments, ADT, boot-args). We copy it into the kernel-managed RAM
 * window the ADT names (the 2 GiB bank at 0x880000000, free of
 * firmware carve-outs), build boot_args and jump to XNU's physical
 * entry with the MMU off.
 *
 * Every step is drawn on the S-Boot framebuffer and appended to
 * both ramoops zones, so after a forced reboot into Lineage
 * recovery the log can be read back with dd from the zone
 * addresses below.
 */
#include <stdint.h>
#include "fdt.h"
#include "font.h"

/* ---- board facts (Gate 0 hardware map + v0.1 probe, live DT) ---- */
#define FB_BASE			0xCA000000UL	/* exynos,fb_rmem reservation */
#define FB_W			1200
#define FB_H			2000
#define FB_STRIDE		(FB_W * 4)
#define RAMOOPS_CONSOLE		0x8F0000000UL	/* top bank, above XNU window */
#define RAMOOPS_CONSOLE_SIZE	0x80000UL
#define PRZ_SIG			0x43474244U	/* "DBGC" */
#define XNU_MARKER_PHYS		0x8F007F000UL	/* console + size - 0x1000; must match A5_ENTRY_MARKER_PHYS in patch 0125 */
#define LOW_RAM_BASE		0x80000000UL	/* initrd must be in the low bank */
#define LOW_RAM_END		0xBAB00000UL	/* live-DT bank 0 end */
#define XNU_RAM_BASE		0x880000000UL	/* 2 GiB high bank */
#define XNU_RAM_END		0x900000000UL
#define PAGE_SIZE		4096UL
#define BOOT_LINE_LENGTH	608
/* Fallback if /chosen lacks the initrd properties: the stock v2
 * header's ramdisk_addr (0x11000000) + Samsung's 0x70000000 base.
 * The payload self-describes its segments, so the synthetic end
 * only bounds the header checks. */
#define INITRD_FALLBACK		0x81000000UL
#define INITRD_FALLBACK_LEN	0x4000000UL	/* 64 MiB synthetic bound */

/* ---- persistent log ----
 * The same text goes to two ramoops zones with separate headers: the
 * console zone and the pmsg zone. A forced reboot flips a few RAM
 * bits; when one flips a zone header, a pstore reader drops that
 * zone, the other copy usually survives. Our read-back is a raw dd
 * from Lineage recovery, so the zones only need to persist. */
struct prz {
	uint32_t sig, start, size;
	uint8_t data[];
};
#define RAMOOPS_PMSG		0x8F0100000UL	/* after console zone + gap */
static volatile struct prz *const prz = (volatile struct prz *)RAMOOPS_CONSOLE;
static volatile struct prz *const prz2 = (volatile struct prz *)RAMOOPS_PMSG;
#define PRZ_DATA_MAX	(RAMOOPS_CONSOLE_SIZE - 12)
static uint32_t log_len, log2_len;

static void prz_put(volatile struct prz *z, uint32_t *len, char c)
{
	if (*len >= PRZ_DATA_MAX)
		return;
	z->data[(*len)++] = (uint8_t)c;
	z->start = *len;
	z->size = *len;
}

/* console zone only: used for the XNU marker padding */
static void log_ch1(char c)
{
	prz_put(prz, &log_len, c);
}

static void log_ch(char c)
{
	prz_put(prz, &log_len, c);
	prz_put(prz2, &log2_len, c);
}

/* ---- screen console ---- */
static volatile uint32_t *const fb = (volatile uint32_t *)FB_BASE;
#define SCALE	3
#define CELL_W	(8 * SCALE)
#define CELL_H	(16 * SCALE + 6)
#define COLS	((FB_W - 48) / CELL_W)
#define ROWS	((FB_H - 160) / CELL_H)
static int row, col;
static uint32_t fg = 0xffffffffU;

static void fill(int x0, int y0, int w, int h, uint32_t c)
{
	for (int y = y0; y < y0 + h && y < FB_H; y++)
		for (int x = x0; x < x0 + w && x < FB_W; x++)
			fb[y * (FB_STRIDE / 4) + x] = c;
}

static void scr_ch(char c)
{
	if (c == '\n' || col >= COLS) {
		col = 0;
		row = (row + 1) % ROWS;
		fill(0, 120 + row * CELL_H, FB_W, CELL_H, 0xff000000U);
		if (c == '\n')
			return;
	}
	if (c < 0x20 || c > 0x7e)
		c = '?';
	const unsigned char *g = font8x16[c - 0x20];
	int x0 = 24 + col * CELL_W, y0 = 120 + row * CELL_H;
	for (int gy = 0; gy < 16; gy++)
		for (int gx = 0; gx < 8; gx++)
			fill(x0 + gx * SCALE, y0 + gy * SCALE, SCALE, SCALE,
			     (g[gy] & (0x80 >> gx)) ? fg : 0xff000000U);
	col++;
}

static void out(const char *s)
{
	while (*s) {
		log_ch(*s);
		scr_ch(*s++);
	}
}

static void hex(uint64_t v)
{
	static const char digits[] = "0123456789abcdef";
	char b[19] = "0x";
	int n = 2, started = 0;
	for (int i = 60; i >= 0; i -= 4) {
		int d = (v >> i) & 0xf;
		if (d || started || i == 0) {
			b[n++] = digits[d];
			started = 1;
		}
	}
	b[n] = 0;
	out(b);
}

static void kv(const char *k, uint64_t v)
{
	out(k);
	out("=");
	hex(v);
	out(" ");
}

/* ---- payload (tools/mkpayload.py v1) ---- */
struct payload_seg {
	uint64_t vmaddr, vmsize, file_off, file_size;
};
struct payload {
	char magic[8];
	uint32_t version, nsegs;
	uint64_t virt_base, entry_va, adt_off, adt_size, kernel_end;
	uint64_t phys_base, mem_size;
	char cmdline[BOOT_LINE_LENGTH];
	struct payload_seg segs[];
};
struct boot_video {
	uint64_t v_baseAddr, v_display, v_rowBytes, v_width, v_height, v_depth;
};
struct boot_args {
	uint16_t Revision, Version;
	uint64_t virtBase, physBase, memSize, topOfKernelData;
	struct boot_video Video;
	uint32_t machineType;
	uint64_t deviceTreeP;
	uint32_t deviceTreeLength;
	char CommandLine[BOOT_LINE_LENGTH];
	uint64_t bootFlags, memSizeActual;
};
_Static_assert(__builtin_offsetof(struct payload, segs) == 0x2a8, "payload layout");
_Static_assert(__builtin_offsetof(struct boot_args, CommandLine) == 108, "boot_args layout");
_Static_assert(sizeof(struct boot_args) == 736, "boot_args size");

uint64_t dl_boot_args;	/* read by start.S */

/* MMU off: everything is Device memory, keep accesses naturally aligned. */
static void copy(uintptr_t dst, uintptr_t src, uint64_t n)
{
	if (!((dst | src) & 7)) {
		for (; n >= 8; n -= 8, dst += 8, src += 8)
			*(volatile uint64_t *)dst = *(volatile uint64_t *)src;
	}
	for (; n; n--, dst++, src++)
		*(volatile uint8_t *)dst = *(volatile uint8_t *)src;
}

static void zero(uintptr_t dst, uint64_t n)
{
	for (; n && (dst & 7); n--, dst++)
		*(volatile uint8_t *)dst = 0;
	for (; n >= 8; n -= 8, dst += 8)
		*(volatile uint64_t *)dst = 0;
	for (; n; n--, dst++)
		*(volatile uint8_t *)dst = 0;
}

static void clean(uintptr_t start, uintptr_t end)
{
	uint64_t ctr;
	__asm__ volatile("mrs %0, ctr_el0" : "=r"(ctr));
	uintptr_t line = 4UL << ((ctr >> 16) & 0xf);
	for (uintptr_t p = start & ~(line - 1); p < end; p += line)
		__asm__ volatile("dc civac, %0" : : "r"(p) : "memory");
	__asm__ volatile("dsb sy" ::: "memory");
}

static int magic_ok(const volatile char *m)
{
	const char *want = "SWEETXNU";
	for (int i = 0; i < 8; i++)
		if (m[i] != want[i])
			return 0;
	return 1;
}

static uint64_t fail(const char *why)
{
	fg = 0xffff4040U;
	out("FAIL: ");
	out(why);
	out("\nHold POWER+VOL DOWN, then POWER+VOL UP -> Lineage recovery\n");
	return 0;
}

/* Leave an 8-byte hole at XNU_MARKER_PHYS inside the pstore text. XNU's
 * start_first_cpu stores "XNUELTE1" there (0125 A5_ENTRY_MARKER_PHYS). */
static void reserve_marker(void)
{
	uint32_t at = (uint32_t)(XNU_MARKER_PHYS - (RAMOOPS_CONSOLE + 12));
	const char *tag = "\nXNU entry marker: [";
	uint32_t tag_len = 0;
	while (tag[tag_len])
		tag_len++;
	while (log_len < at - tag_len)
		log_ch1(log_len % 128 == 127 ? '\n' : ' ');
	for (uint32_t i = 0; i < tag_len; i++)
		log_ch1(tag[i]);
	for (int i = 0; i < 8; i++)
		log_ch1('-');
	log_ch1(']');
	log_ch1('\n');
}

uint64_t dl_main(uintptr_t dtb, uint64_t el, uint64_t sctlr)
{
	prz->sig = PRZ_SIG;
	prz->start = prz->size = 0;
	prz2->sig = PRZ_SIG;
	prz2->start = prz2->size = 0;
	fill(0, 0, FB_W, FB_H, 0xff000000U);
	fg = 0xffffff00U;
	out("GTA4XL LOADER BEGIN  (ios-gta4xlwifi XNU loader)\n");
	fg = 0xffffffffU;
	uint64_t mpidr, cntfrq;
	__asm__ volatile("mrs %0, mpidr_el1" : "=r"(mpidr));
	__asm__ volatile("mrs %0, cntfrq_el0" : "=r"(cntfrq));
	kv("EL", el);
	kv("SCTLR", sctlr);
	kv("DTB", dtb);
	out("\n");
	kv("MPIDR", mpidr);
	kv("CNTFRQ", cntfrq);
	out("\n");
	if (el != 1)
		return fail("not entered at EL1");

	uint64_t rd_start, rd_end;
	if (!fdt_chosen_u64(dtb, "linux,initrd-start", &rd_start) ||
	    !fdt_chosen_u64(dtb, "linux,initrd-end", &rd_end)) {
		rd_start = INITRD_FALLBACK;
		rd_end = INITRD_FALLBACK + INITRD_FALLBACK_LEN;
		out("no initrd in /chosen - header fallback\n");
	}
	kv("initrd", rd_start);
	kv("end", rd_end);
	out("\n");
	if (rd_start < LOW_RAM_BASE || rd_end > LOW_RAM_END || rd_end <= rd_start)
		return fail("initrd outside low RAM");

	const volatile struct payload *p = (const volatile struct payload *)rd_start;
	uint64_t length = rd_end - rd_start;
	if (length < sizeof(struct payload) || !magic_ok(p->magic) || p->version != 1)
		return fail("initrd is not a SWEETXNU v1 payload");
	uint64_t nsegs = p->nsegs;
	kv("segs", nsegs);
	kv("virt", p->virt_base);
	kv("entry", p->entry_va);
	out("\n");
	kv("phys", p->phys_base);
	kv("mem", p->mem_size);
	kv("adt", p->adt_size);
	out("\n");
	if (!nsegs || nsegs > 32 ||
	    __builtin_offsetof(struct payload, segs) + nsegs * sizeof(struct payload_seg) > length ||
	    p->adt_off > length || p->adt_size > length - p->adt_off)
		return fail("bad payload header");
	if (p->phys_base < XNU_RAM_BASE || p->phys_base >= XNU_RAM_END || !p->mem_size ||
	    p->mem_size > XNU_RAM_END - p->phys_base ||
	    p->entry_va < p->virt_base || p->kernel_end < p->virt_base)
		return fail("payload RAM outside the 0x880000000 bank");
	uintptr_t mem_end = p->phys_base + p->mem_size;
	uintptr_t kernel_end = p->phys_base + (p->kernel_end - p->virt_base);
	if (kernel_end >= mem_end)
		return fail("kernel larger than RAM window");

	/* iBoot hands XNU zeroed RAM; S-Boot leaves the previous OS's data.
	 * On the S8, XNU hung right after its version line, in
	 * vm_mem_bootstrap, depending on how the phone was rebooted. */
	out("zeroing XNU RAM...\n");
	zero(p->phys_base, p->mem_size);
	out("zeroed\n");

	for (uint64_t i = 0; i < nsegs; i++) {
		const volatile struct payload_seg *s = &p->segs[i];
		if (s->vmaddr < p->virt_base || s->file_size > s->vmsize ||
		    s->file_off > length || s->file_size > length - s->file_off ||
		    s->vmsize > p->mem_size || s->vmaddr - p->virt_base > p->mem_size - s->vmsize)
			return fail("bad segment");
		uintptr_t dst = p->phys_base + (s->vmaddr - p->virt_base);
		copy(dst, rd_start + s->file_off, s->file_size);
		zero(dst + s->file_size, s->vmsize - s->file_size);
		clean(dst, dst + s->vmsize);
		out("seg ");
		hex(i);
		out(" -> ");
		hex(dst);
		out(" ");
		hex(s->vmsize);
		out("\n");
	}

	uintptr_t adt_pa = kernel_end;
	uintptr_t ba_pa = (adt_pa + p->adt_size + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1);
	if (ba_pa + PAGE_SIZE > mem_end)
		return fail("no room for ADT/boot_args");
	copy(adt_pa, rd_start + p->adt_off, p->adt_size);
	zero(ba_pa, PAGE_SIZE);
	volatile struct boot_args *ba = (volatile struct boot_args *)ba_pa;
	ba->Revision = 2;
	ba->Version = 2;
	ba->virtBase = p->virt_base;
	ba->physBase = p->phys_base;
	ba->memSize = p->mem_size;
	ba->topOfKernelData = ba_pa + PAGE_SIZE;
	ba->deviceTreeP = p->virt_base + (adt_pa - p->phys_base);
	ba->deviceTreeLength = (uint32_t)p->adt_size;
	for (int i = 0; i < BOOT_LINE_LENGTH; i++)
		ba->CommandLine[i] = p->cmdline[i];
	ba->memSizeActual = p->mem_size;
	clean(adt_pa, ba_pa + PAGE_SIZE);

	uintptr_t entry_pa = p->phys_base + (p->entry_va - p->virt_base);
	if (entry_pa >= kernel_end)
		return fail("entry outside kernel");
	dl_boot_args = ba_pa;
	kv("adt_pa", adt_pa);
	kv("boot_args", ba_pa);
	out("\n");
	kv("entry_pa", entry_pa);
	out("\ncmdline: ");
	for (int i = 0; i < BOOT_LINE_LENGTH && p->cmdline[i]; i++) {
		char c[2] = { p->cmdline[i], 0 };
		out(c);
	}
	out("\n");
	fg = 0xff40ff40U;
	out("\nJUMP TO XNU\n");
	reserve_marker();
	clean(RAMOOPS_CONSOLE, RAMOOPS_CONSOLE + RAMOOPS_CONSOLE_SIZE);
	clean(RAMOOPS_PMSG, RAMOOPS_PMSG + RAMOOPS_CONSOLE_SIZE);
	return entry_pa;
}

void dl_exception(uint64_t slot)
{
	uint64_t esr, elr, far;
	__asm__ volatile("mrs %0, esr_el1" : "=r"(esr));
	__asm__ volatile("mrs %0, elr_el1" : "=r"(elr));
	__asm__ volatile("mrs %0, far_el1" : "=r"(far));
	fg = 0xffff4040U;
	out("\nLOADER EXCEPTION ");
	kv("slot", slot);
	kv("ESR", esr);
	kv("ELR", elr);
	kv("FAR", far);
	out("\n");
	for (;;)
		__asm__ volatile("wfe");
}

/* gcc may emit calls for struct copies; keep the image self-contained. */
void *memset(void *d, int c, unsigned long n)
{
	unsigned char *q = d;
	while (n--)
		*q++ = (unsigned char)c;
	return d;
}

void *memcpy(void *d, const void *s, unsigned long n)
{
	unsigned char *q = d;
	const unsigned char *r = s;
	while (n--)
		*q++ = *r++;
	return d;
}
