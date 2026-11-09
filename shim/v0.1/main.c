/* Gate 2 probe shim v0.1: framebuffer heartbeat (as v0) plus a
 * boot-state readout painted under the pass counter:
 *   row 1: MPIDR_EL1 low 16 bits as 4 hex digits, then CurrentEL
 *   row 2: CNTFRQ_EL0 low 32 bits as 8 hex digits
 * The Gate 2 design keys off these: which core S-Boot boots on
 * (A73 MPIDR 0x0 vs A53 MPIDR 0x100), the EL the shim runs at,
 * and whether the timer frequency register is really
 * unprogrammed (the stock DT reading says S-Boot never sets it,
 * which is why the ADT must carry timebase-frequency). */
#include <stdint.h>

#define FB_BASE   0xCA000000ull
#define FB_W      1200
#define FB_H      2000
#define FB_STRIDE 1200          /* pixels per row, confirmed by v0 */
#define FB_BYTES  (FB_STRIDE * FB_H * 4)

static const uint32_t bands[8] = {
    0xFF000000, /* black   */
    0xFFFF0000, /* red     */
    0xFF00FF00, /* green   */
    0xFF0000FF, /* blue    */
    0xFFFFFF00, /* yellow  */
    0xFF00FFFF, /* cyan    */
    0xFFFF00FF, /* magenta */
    0xFFFFFFFF, /* white   */
};

static void clean_cache_range(uintptr_t start, uintptr_t end)
{
    for (uintptr_t p = start; p < end; p += 64)
        __asm__ volatile("dc cvac, %0" :: "r"(p) : "memory");
    __asm__ volatile("dsb sy" ::: "memory");
}

static void delay(void)
{
    for (volatile uint64_t i = 0; i < 60000000ull; i++)
        ;
}

/* 3x5 block font, hex digits 0-F */
static const uint8_t font[16][5] = {
    {0x7,0x5,0x5,0x5,0x7}, {0x2,0x6,0x2,0x2,0x7},
    {0x7,0x1,0x7,0x4,0x7}, {0x7,0x1,0x3,0x1,0x7},
    {0x5,0x5,0x7,0x1,0x1}, {0x7,0x4,0x7,0x1,0x7},
    {0x7,0x4,0x7,0x5,0x7}, {0x7,0x1,0x1,0x2,0x2},
    {0x7,0x5,0x7,0x5,0x7}, {0x7,0x5,0x7,0x1,0x7},
    {0x7,0x5,0x7,0x5,0x5}, {0x6,0x5,0x6,0x5,0x6},
    {0x7,0x4,0x4,0x4,0x7}, {0x6,0x5,0x5,0x5,0x6},
    {0x7,0x4,0x6,0x4,0x7}, {0x7,0x4,0x6,0x4,0x4},
};

static void draw_digit(volatile uint32_t *fb, int x0, int y0, int scale,
                       int digit, uint32_t fg, uint32_t bg)
{
    for (int r = 0; r < 5; r++)
        for (int c = 0; c < 3; c++) {
            uint32_t col = (font[digit][r] >> (2 - c)) & 1 ? fg : bg;
            for (int dy = 0; dy < scale; dy++)
                for (int dx = 0; dx < scale; dx++)
                    fb[(y0 + r * scale + dy) * FB_STRIDE + x0 + c * scale + dx] = col;
        }
}

/* draw a value as `digits` hex chars, most significant first */
static void draw_hex(volatile uint32_t *fb, int x0, int y0, int scale,
                     uint64_t val, int digits)
{
    for (int i = 0; i < digits; i++) {
        int shift = (digits - 1 - i) * 4;
        draw_digit(fb, x0 + i * (3 * scale + scale / 2), y0, scale,
                   (int)((val >> shift) & 0xF), 0xFFFFFFFF, 0xFF000000);
    }
}

void kmain(void)
{
    volatile uint32_t *fb = (volatile uint32_t *)FB_BASE;
    uint64_t mpidr, el, cntfrq;
    __asm__ volatile("mrs %0, mpidr_el1" : "=r"(mpidr));
    __asm__ volatile("mrs %0, CurrentEL" : "=r"(el));
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(cntfrq));
    uint32_t pass = 0;

    for (;;) {
        for (int y = 0; y < FB_H; y++) {
            uint32_t col = bands[((y * 8) / FB_H + pass) & 7];
            for (int x = 0; x < FB_W; x++)
                fb[y * FB_STRIDE + x] = col;
        }
        /* pass counter, two digits, top-left, black on white box */
        draw_digit(fb, 40, 40, 24, (pass / 10) % 10, 0xFF000000, 0xFFFFFFFF);
        draw_digit(fb, 130, 40, 24, pass % 10, 0xFF000000, 0xFFFFFFFF);
        /* probe rows, white on black boxes */
        draw_hex(fb, 40, 220, 16, mpidr & 0xFFFF, 4);        /* MPIDR[15:0] */
        draw_digit(fb, 40 + 4 * 56 + 30, 220, 16,
                   (int)((el >> 2) & 3), 0xFFFFFFFF, 0xFF000000); /* EL */
        draw_hex(fb, 40, 340, 12, cntfrq & 0xFFFFFFFFull, 8); /* CNTFRQ */
        clean_cache_range(FB_BASE, FB_BASE + FB_BYTES);
        pass++;
        delay();
    }
}
