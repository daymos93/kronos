#!/bin/bash



ROOTDIR=$(pwd)

echo "Install CAEN libraries for DIGITIZER"

echo "Install kernel headers" # needed for USB driver for building
sudo yum -y install kernel-devel gnuplot automake makeinfo


echo "Install CAEN VME library"
cd $ROOTDIR
cd CAENVMELib-2.50/lib
sudo sh install_x64


echo "Install CAEN Comm driver"
cd $ROOTDIR
cd CAENComm-1.2/lib
sudo sh install_x64



echo "Install CAEN USB driver"
cd $ROOTDIR
cd CAENUSBdrvB-1.5.2
make
sudo make install


echo "Install CAEN Digitizer Library"
cd $ROOTDIR
cd CAENDigitizer_2.7.9
sudo sh install_64



echo "Install CAEN WaveDump"
cd $ROOTDIR
cd DIGITIZER_DAQ
chmod 755 configure
./configure
make
