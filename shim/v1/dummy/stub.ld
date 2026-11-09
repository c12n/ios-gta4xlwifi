OUTPUT_FORMAT("elf64-littleaarch64")
ENTRY(_stub_start)
SECTIONS {
	. = 0xFFFFFE0000000000;
	.text : { *(.text) }
	. = ALIGN(8);
	_end = .;
}
