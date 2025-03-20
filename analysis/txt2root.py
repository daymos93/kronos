
import sys, os, glob, shutil, json, math, re, random, numpy
import ROOT

ROOT.gROOT.SetBatch()
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)


def loadFiles(dir):

    nEvents = 0
    files = []

    for i in range(0, 18):
        if i < 16:
            lines = [line.rstrip('\n') for line in open("%s/wave_%d.txt" % (dir, i))]
            files.append(lines)
            nEvents = len(lines)
        else:
            lines = [line.rstrip('\n') for line in open("%s/TR_0_%d.txt" % (dir, i-16))]
            files.append(lines)
            nEvents = len(lines)

    nEvents = nEvents / (1024 + 8)
    return nEvents, files
  
    
def getInt(s):
    return int(re.search(r'\d+', s).group())
    
def getFloat(s):
    return float(re.search(r'\d+\.\d+', s).group())


if __name__ == "__main__":


    ## dir: ROOT directory of all raw data files 
    dir = "."

    # record length: Record Length in the digitizer setting (i.e. # timing samples)
    # The calibration from bits to time (ns) depends on the digitizer sampling rate, and the conversion will be done in the analyzer
    record_length = 1024


    ##############################################################################################
    
    # Define fixed (uncalibrated) time vector of 1024 bits
    time = ROOT.TVectorD(record_length)
    for i in range(0, record_length): time[i] = i

    # loop over all HVXX_DIGITIZER directories and open the wave.txt files
    for x in os.listdir(dir):
    
        if not "_DIGITIZER" in x: continue

        HVdir = dir + "/" + x
        print(" > running in dir %s" % HVdir)


        # prepare tree and arrays
        tFull = ROOT.TTree("data", "data") # store all events in the tree

        evNum = numpy.zeros(1, dtype=int)
        trgTime = numpy.zeros(1, dtype=int)  

        tFull.Branch("evNum", evNum, "evNum/I")
        tFull.Branch("trgTime", trgTime, "trgTime/I")

        
        pulses = []
        for i in range(0, 18):
            pulse = ROOT.vector('double')()
            pulses.append(pulse)
            
            if i < 16 : tFull.Branch("pulse_ch%d" % i, pulses[i]) # , "pulse[1024]/F"
            else: tFull.Branch("pulse_TR_0%d" % (i-16), pulses[i]) # , "pulse[1024]/F"


        # load all waves into memory
        nEvents, files = loadFiles(HVdir)

        print("  > amount of events collected:", nEvents)

        ff = math.ceil(nEvents / (nEvents*0.05))
        entriesWritten = 0

        for i in range(0, len(files[0])):

            if "Record Length" in files[0][i]: continue
            elif "BoardID" in files[0][i]: continue
            elif "Channel" in files[0][i]: continue
            elif "Event Number" in files[0][i]: evNum[0] = getInt(files[0][i])
            elif "Pattern" in files[0][i]: continue
            elif "Trigger Time Stamp" in files[0][i]: trgTime[0] = getInt(files[0][i])
            elif "DC offset (DAC)" in files[0][i]: continue
            elif "Start Index Cell" in files[0][i]: continue
            else:

                for j in range(0, 18): pulses[j].push_back(float(files[j][i])) 
                
                #this can be used to calibrate the time bits to ns, depending on the sampling rate
                #for j in range(0, 16): pulses[j].push_back(float(files[j][i]) * 1000 / 4096) 


            # write and clean
            if (i+1)%(1024+8) == 0:

                entriesWritten += 1
                tFull.Fill()
                for k in range(0, 18): pulses[k].clear()


        # write tree to ROOT file
        f1 = ROOT.TFile("%s/%s.root" % (HVdir, x), "recreate")
        tFull.Write()
        time.Write("time")
        f1.Close()


        # clear memory
        files = None 
        
