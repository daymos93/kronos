

import sys,os,time
from subprocess import call
import glob
import shutil

runfile = "/home/webdcs/webdcs/RUN/run"
daqinifile = "/home/webdcs/webdcs/RUN/daq_digitizer.ini" # updated by WebDCS

RUN = ""
HV = -1
RUNID = -1
TRIGGERS = -1


def readRunFile():

    global RUN
    call("sshpass -p 'UserlabGIF++' scp webdcs@webdcs.cern.ch:/var/operation/RUN/run /home/webdcs/webdcs/RUN/", shell=True);
    with open(runfile, 'r') as f: RUN = f.readline().rstrip().rstrip('\n')

def setRunFile(f):

    cmd = "echo -n '%s' | sshpass -p 'UserlabGIF++' ssh webdcs@webdcs.cern.ch 'cat > /var/operation/RUN/run'" % f
    call(cmd, shell=True)


def readINIFile():

    global HV,RUNID,TRIGGERS

    with open(daqinifile, 'r') as f:
     
        for line in f:
     
            line = line.rstrip()

            if "W_MAXTRIGGERS" in line: TRIGGERS = int(line.split(" ")[1])
            if "W_RUNID" in line: RUNID = int(line.split(" ")[1])
            if "W_HVPOINT" in line: HV = int(line.split(" ")[1])

if __name__ == "__main__":

    RUN = ""
    setRunFile("DAQ_RDY") # by default DAQ is ready
    readINIFile()

    while RUN != "STOP" or RUN != "KILL": # run until stop command is given by WebDCS
    
        #readINIFile()
        readRunFile()
        if RUN == "STOP" or RUN == "KILL": break
    
        # start DAQ (the DAQ waits for the START command of the DCS)
        if RUN == "START":

            # Read config file and make directories
            readINIFile()

            DIR = "/home/webdcs/webdcs/HVSCAN/%06d" % (RUNID)
            if not os.path.exists(DIR): os.makedirs(DIR)
            DIR = "/home/webdcs/webdcs/HVSCAN/%06d/HV%d" % (RUNID, HV)
            if os.path.exists(DIR): shutil.rmtree(DIR)
            os.makedirs(DIR)


            # Run DAQ
            print "START DAQ"
            setRunFile("RUNNING") # set runfile to running
            call("/home/webdcs/webdcs/DAQ/src/wavedump %d %d" % (TRIGGERS, RUNID), shell=True) # ideally should return DAQ_RDY
            setRunFile("DAQ_RDY") # end of run

            # MOVE ALL THE FILES AFTER THE RUN ALSO THE DAQ INI FILE
            for file in glob.glob("wave_*"):
                shutil.move(file, DIR)

            shutil.copy(daqinifile, DIR)

        # now wait for START command of WebDCS
        time.sleep(5)
        print "wait.."
   


    
    
