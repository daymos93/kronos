#!/bin/bash -e
cp v1718_name.sh /usr/bin
echo "KERNEL==\"v1718_[0-9]\", PROGRAM=\"/usr/bin/v1718_name.sh\", SYMLINK+=\"usb/%c\", MODE=\"0666\"" > /etc/udev/rules.d/10-CAEN-USB.rules
udevadm control --reload-rules
