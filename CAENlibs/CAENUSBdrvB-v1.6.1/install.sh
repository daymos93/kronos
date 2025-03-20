#!/bin/bash -e
VERSION=1.6.1

sed -e "s/\${version}/$VERSION/" dkms.conf.in > dkms.conf

# Remove module if already loaded
rmmod CAENUSBdrvB 2> /dev/null || true

# If the same version is already installed, it will be overwritten
dkms uninstall CAENUSBdrvB/$VERSION -q || true
dkms remove CAENUSBdrvB/$VERSION -q --all || true

cp -R . /usr/src/CAENUSBdrvB-$VERSION
dkms add CAENUSBdrvB/$VERSION
dkms build CAENUSBdrvB/$VERSION
dkms install CAENUSBdrvB/$VERSION --force

# Reload the module
modprobe CAENUSBdrvB
