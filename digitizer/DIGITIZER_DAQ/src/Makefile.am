datadir=~/.wavedump/
bin_PROGRAMS=wavedump
wavedump_SOURCES=WaveDump.c WDconfig.c WDplot.c X742CorrectionRoutines.c fft.c keyb.c
wavedump_LDADD = -lCAENComm -lCAENDigitizer -lm -lpthread
AM_CPPFLAGS = -I../include
AM_CFLAGS=  -fPIC
dist_data_DATA=../Setup/WaveDumpConfig.txt