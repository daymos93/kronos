#!/bin/bash -e
rm /etc/udev/rules.d/10-CAEN-USB.rules
rm /usr/bin/v1718_name.sh
udevadm control --reload-rules
