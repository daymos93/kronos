#!/bin/bash

NUM=0
STR=$(ls -v -d /dev/usb/v1718_* 2>/dev/null | grep "/v1718_[0-9]\+\$") # this should match only devices
if [ -n "${STR}" ]; then
  for D in $STR; do
    DN=$(readlink -m $D)
    if [ "$DN" == "$DEVNAME" ]; then
      # link to this dev already exists, print the existing
      # name and exit with success
      basename $D
      exit 0
    fi
  done
  A=( ${STR} )
  LAST=${A[${#A[@]} - 1]}
  NUM=$(echo ${LAST} | sed 's|^.*v1718_||')
  NUM=$(($NUM+1))
fi

echo "v1718_${NUM}"

exit 0
