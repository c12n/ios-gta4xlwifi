/* Dummy "kernel" for the Gate 2 loader smoke test. Entered exactly
 * like XNU (EL1, MMU off, x0 = boot_args PA). Paints the framebuffer
 * a pattern the loader never draws (cyan/magenta checkerboard),
 * writes DUMMYOK! over the loader's XNU entry-marker slot, leaves
 * the boot_args PA in the first framebuffer pixels, then parks.
 * If this appears on screen, the loader's whole handoff path -
 * payload discovery, segment copy, ADT/boot_args placement, jump -
 * worked with zero XNU involvement. */
	.text
	.globl _stub_start
_stub_start:
	ldr	x1, =0xCA000000		/* FB base */
	str	w0, [x1]		/* boot_args PA low in pixel 0 */
	lsr	x0, x0, #32
	str	w0, [x1, #4]		/* boot_args PA high in pixel 1 */
	mov	x2, #0			/* y */
.Lrow:
	mov	x3, #0			/* x */
	mov	x8, #4800		/* stride bytes */
	mul	x9, x2, x8		/* row base offset */
.Lcol:
	add	x4, x2, x3
	lsr	x4, x4, #7
	and	x4, x4, #1
	ldr	w5, =0xFF00FFFF		/* cyan */
	ldr	w6, =0xFFFF00FF		/* magenta */
	cmp	x4, #0
	csel	w5, w5, w6, eq
	add	x7, x1, x9
	add	x7, x7, x3, lsl #2
	str	w5, [x7]
	add	x3, x3, #1
	cmp	x3, #1200
	b.lo	.Lcol
	add	x2, x2, #1
	cmp	x2, #2000
	b.lo	.Lrow
	/* marker: "DUMMYOK!" at the loader's XNU_MARKER_PHYS */
	ldr	x1, =0x8F007F000
	ldr	x2, =0x214B4F594D4D5544	/* "DUMMYOK!" little-endian */
	str	x2, [x1]
	/* clean FB + marker to PoC */
	ldr	x1, =0xCA000000
	ldr	x2, =0xCA960000		/* FB end: +1200*2000*4 */
.Lcl:	dc	cvac, x1
	add	x1, x1, #64
	cmp	x1, x2
	b.lo	.Lcl
	ldr	x1, =0x8F007F000
	dc	cvac, x1
	dsb	sy
1:	wfe
	b	1b
