/* Gate 1 shim v0: framebuffer heartbeat.
 * Proves S-Boot takeover: draws 8 horizontal color bands to the
 * S-Boot framebuffer reservation (0xCA000000, 1200x2000, assumed
 * 32bpp XRGB, stride = width) plus a block-digit pass counter in
 * the top-left corner, rotating the bands once per pass. If the
 * stride/format assumption is wrong the picture shears or shifts
 * color, which is itself the diagnostic we want from a photo. */
#include <stdint.h>

#define FB_BASE   0xCA000000ull
#define FB_W      1200
#define FB_H      2000
#define FB_STRIDE 1200          /* pixels per row, assumption v0 */
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
    /* dc cvac to Point of Coherency, 64-byte lines */
    for (uintptr_t p = start; p < end; p += 64)
        __asm__ volatile("dc cvac, %0" :: "r"(p) : "memory");
    __asm__ volatile("dsb sy" ::: "memory");
}

static void delay(void)
{
    /* ~0.5-1 s of busy loop at 1-2 GHz; CNTFRQ is unprogrammed by
     * S-Boot, so count instructions instead of reading the timer. */
    for (volatile uint64_t i = 0; i < 60000000ull; i++)
        ;
}

/* 3x5 block font, one digit */
static const uint8_t font[10][5] = {
    {0x7,0x5,0x5,0x5,0x7}, {0x2,0x6,0x2,0x2,0x7},
    {0x7,0x1,0x7,0x4,0x7}, {0x7,0x1,0x3,0x1,0x7},
    {0x5,0x5,0x7,0x1,0x1}, {0x7,0x4,0x7,0x1,0x7},
    {0x7,0x4,0x7,0x5,0x7}, {0x7,0x1,0x1,0x2,0x2},
    {0x7,0x5,0x7,0x5,0x7}, {0x7,0x5,0x7,0x1,0x7},
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

void kmain(void)
{
    volatile uint32_t *fb = (volatile uint32_t *)FB_BASE;
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
        clean_cache_range(FB_BASE, FB_BASE + FB_BYTES);
        pass++;
        delay();
    }
}
