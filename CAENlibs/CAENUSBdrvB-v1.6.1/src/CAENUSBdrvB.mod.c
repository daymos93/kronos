#include <linux/module.h>
#define INCLUDE_VERMAGIC
#include <linux/build-salt.h>
#include <linux/elfnote-lto.h>
#include <linux/export-internal.h>
#include <linux/vermagic.h>
#include <linux/compiler.h>

#ifdef CONFIG_UNWINDER_ORC
#include <asm/orc_header.h>
ORC_HEADER;
#endif

BUILD_SALT;
BUILD_LTO_INFO;

MODULE_INFO(vermagic, VERMAGIC_STRING);
MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};

#ifdef CONFIG_MITIGATION_RETPOLINE
MODULE_INFO(retpoline, "Y");
#endif



static const char ____versions[]
__used __section("__versions") =
	"\x28\x00\x00\x00\xb3\x1c\xa2\x87"
	"__ubsan_handle_out_of_bounds\0\0\0\0"
	"\x18\x00\x00\x00\x48\xab\x46\x36"
	"usb_bulk_msg\0\0\0\0"
	"\x1c\x00\x00\x00\x48\x9f\xdb\x88"
	"__check_object_size\0"
	"\x18\x00\x00\x00\xe1\xbe\x10\x6b"
	"_copy_to_user\0\0\0"
	"\x18\x00\x00\x00\xfc\xe2\xed\x1c"
	"usb_clear_halt\0\0"
	"\x20\x00\x00\x00\x5d\x7b\xc1\xe2"
	"__SCT__might_resched\0\0\0\0"
	"\x1c\x00\x00\x00\xcb\xf6\xfd\xf0"
	"__stack_chk_fail\0\0\0\0"
	"\x10\x00\x00\x00\xba\x0c\x7a\x03"
	"kfree\0\0\0"
	"\x1c\x00\x00\x00\x06\x50\x66\x0b"
	"usb_deregister_dev\0\0"
	"\x1c\x00\x00\x00\x63\xa5\x03\x4c"
	"random_kmalloc_seed\0"
	"\x18\x00\x00\x00\x1d\x07\x60\x20"
	"kmalloc_caches\0\0"
	"\x20\x00\x00\x00\xee\xfb\xb4\x10"
	"__kmalloc_cache_noprof\0\0"
	"\x1c\x00\x00\x00\x14\x0d\x00\x4a"
	"usb_register_dev\0\0\0\0"
	"\x20\x00\x00\x00\xe9\x0d\x1d\x44"
	"__kmalloc_large_noprof\0\0"
	"\x18\x00\x00\x00\x55\xd5\xa4\xe2"
	"usb_deregister\0\0"
	"\x14\x00\x00\x00\x4b\x8d\xfa\x4d"
	"mutex_lock\0\0"
	"\x18\x00\x00\x00\xc2\x9c\xc4\x13"
	"_copy_from_user\0"
	"\x18\x00\x00\x00\xcd\x71\x07\x58"
	"usb_control_msg\0"
	"\x18\x00\x00\x00\x38\xf0\x13\x32"
	"mutex_unlock\0\0\0\0"
	"\x18\x00\x00\x00\xe3\xb8\xcb\x0d"
	"const_pcpu_hot\0\0"
	"\x14\x00\x00\x00\xbb\x6d\xfb\xbd"
	"__fentry__\0\0"
	"\x1c\x00\x00\x00\xe8\x75\xa3\xef"
	"usb_register_driver\0"
	"\x10\x00\x00\x00\x7e\x3a\x2c\x12"
	"_printk\0"
	"\x1c\x00\x00\x00\xca\x39\x82\x5b"
	"__x86_return_thunk\0\0"
	"\x10\x00\x00\x00\xca\xaf\x26\x66"
	"down\0\0\0\0"
	"\x0c\x00\x00\x00\x66\x69\x2a\xcf"
	"up\0\0"
	"\x20\x00\x00\x00\x54\xea\xa5\xd9"
	"__init_waitqueue_head\0\0\0"
	"\x18\x00\x00\x00\x9f\x0c\xfb\xce"
	"__mutex_init\0\0\0\0"
	"\x18\x00\x00\x00\xde\x9f\x8a\x25"
	"module_layout\0\0\0"
	"\x00\x00\x00\x00\x00\x00\x00\x00";

MODULE_INFO(depends, "");

MODULE_ALIAS("usb:v0547p1002d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v21E1p0000d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v21E1p0001d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v21E1p0011d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v21E1p0019d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v21E1p0015d*dc*dsc*dp*ic*isc*ip*in*");

MODULE_INFO(srcversion, "DFBFB6A12FD93EA0F9B73B3");
