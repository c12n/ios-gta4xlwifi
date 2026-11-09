/* Gate 1 shim v0 - entry from S-Boot.
 * S-Boot hands off per the Linux arm64 boot protocol: MMU off,
 * x0 = physical DTB address, primary CPU only. Physical load
 * address is 0x80080000 (header kernel_addr 0x10008000 plus
 * Samsung's 0x70000000 base offset). */
    .section .text.start
    .global _start
_start:
    msr     daifset, #0xf          /* mask all interrupts */
    ldr     x0, =0x8F000000        /* stack near top of first RAM bank */
    mov     sp, x0
    bl      kmain
1:  wfe
    b       1b
