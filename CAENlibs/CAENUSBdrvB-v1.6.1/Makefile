#=============================================================================
#
#             --- CAEN SpA - Computing Systems Division ---
#
#  Makefile
#
#
#  January  2011 :   Created.
#  February 2013 :   Last Version
#
#=============================================================================

###############################
# Kernel >= 2.6
###############################
# Comment/uncomment the following line to disable/enable debugging
#DEBUG = y

# Add your debugging flag (or not) to EXTRA_CFLAGS 
ifeq ($(DEBUG),y)
  DEBFLAGS = -O -g # "-O" is needed to expand inlines
else
  DEBFLAGS = -O2 -Wall
endif

EXTRA_CFLAGS += $(DEBFLAGS)

ifneq ($(KERNELRELEASE),)
# call from kernel build system

obj-m	:= src/CAENUSBdrvB.o

endif

KERNELDIR ?= /lib/modules/$(shell uname -r)/build
PWD       := $(shell pwd)

default:
	$(MAKE) -C $(KERNELDIR) M=$(PWD) modules

install:
	@./dkms_post_add.sh
	@cp src/CAENUSBdrvB.ko /lib/modules/$(shell uname -r)/kernel/drivers/misc/
	@echo CAENUSBdrvB >> /etc/modules
	@echo "installing CAENUSBdrvB driver.. please wait"
	@depmod -a
	@modprobe CAENUSBdrvB
	@echo "installation done"
uninstall:
	@./dkms_post_remove.sh
	@rm /lib/modules/$(shell uname -r)/kernel/drivers/misc/CAENUSBdrvB.ko
	@sed -i '/CAENUSBdrvB/d' /etc/modules
	@depmod -a
	@echo "driver uninstalled"

all:
	$(MAKE) -C $(KERNELDIR) M=$(PWD) modules

clean:
	rm -rf src/*.o src/*~ src/core src/.depend src/.*.cmd src/*.ko src/*.ko.* src/*.mod.c src/.tmp_versions ./modules.order ./Module.markers ./Module.symvers ./report.log

depend .depend dep:
	$(CC) $(EXTRA_CFLAGS) -M *.c > .depend


ifeq (.depend,$(wildcard .depend))
include .depend
endif
