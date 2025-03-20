import sys
import os

from pycaenhv.wrappers import init_system, deinit_system, get_board_parameters, get_crate_map,  get_channel_parameters,  get_channel_parameter, set_channel_parameter
from pycaenhv.enums import CAENHV_SYSTEM_TYPE, LinkType
from pycaenhv.errors import CAENHVError

import socket
from datetime import datetime
import time

import ROOT

import subprocess

import json
import argparse

import MySQLdb
import MySQLdb.cursors

def log_message(log_file, message):
    # Ensure the log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Get the current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Prepare the log entry
    log_entry = f"{timestamp}.[HVSCAN] {message}\n"
    
    # Append the log entry to the log file
    with open(log_file, 'a') as file:
        file.write(log_entry)
    
    # print(f"{log_entry.strip()}")


# def connect_to_PT_db(): # PT database webdcs Bari 
    
#     #Connecting to the ENV DB to read PT 
#     db = MySQLdb.connect(host='192.135.20.59', user='root', db='webdcs', cursorclass=MySQLdb.cursors.DictCursor) # PT webdcs Bari 
#     cu = db.cursor()
#     #Create cursor and iterate over results
#     cu.execute("SELECT * FROM ENV_SENSOR ORDER BY timestamp DESC LIMIT 1")
#     rs = cu.fetchall()
    
#     T = rs[0]["T"]
#     P = rs[0]["P"]
#     # RH = rs[0]["RH"]

#     return P, T

def connect_to_PT_db(): # PT database INFN Torino 
    
    #Connecting to the ENV DB to read PT 
    db = MySQLdb.connect(host='90.147.203.161', user='kronos', db='labStrada', password='kronos25', cursorclass=MySQLdb.cursors.DictCursor)
    cu = db.cursor()
    #Create cursor and iterate over results
    cu.execute("SELECT date, temperature, pressure, humidity FROM envPar ORDER BY date DESC LIMIT 1")
    rs = cu.fetchall()
    
    T = rs[0]["temperature"]
    P = rs[0]["pressure"]
    # RH = rs[0]["humidity"]

    #print(T, P, "\n")
    
    return P, T





def connectCAEN(ip):
    system_type = CAENHV_SYSTEM_TYPE["SY1527"]
    link_type = LinkType["TCPIP"]
    handle = init_system(system_type, link_type,
                         ip,
                         "user",
                         "user")
    
    return handle
    # try:
    #     # print(f"Got handle: {handle}")
    #     crate_map = get_crate_map(handle)
    #     for name, value in crate_map.items():
    #         print(name, value)
    #     board_parameters = get_board_parameters(handle, 9)
    #     print(f"Board parameters: {board_parameters}")

    #     channel_pars = get_channel_parameter(handle, 9, 0, 'VMon')
    #     print(f"Board channel 0901: {channel_pars}") 



    # except CAENHVError as err:
    #     print(f"Got error: {err}\nExiting ...")
    # finally:
    #     print("Deinitialize.")
    #     deinit_system(handle=handle)
    # print("Bye bye.")

def celsius_to_kelvin(celsius):
    return celsius + 273.15

def PTCorrection(HV):

    P, T = connect_to_PT_db() # connecting to PT DB getting the instant P, T values

    T = celsius_to_kelvin(T) # to K

    # Implement the PTCorrection function
    T0 = 293.15 #K
    P0 = 990 #mbar
    alpha = 0.8 # empiric value set for CMS cavern
    
    beta = (1-alpha) + alpha*P*T0/(P0*T) 

    HV = (1.0*HV)*beta

    return HV  # HV with actual correction calculation

def readRUN(RUN_FILE):
    try:
        with open(RUN_FILE, "r") as fp:  # Use 'with' to automatically close the file
            tmp = fp.read(30).strip()  # Read up to 30 characters and strip any extra whitespace
            global RUN
            RUN = tmp  # Set the global RUN variable to the value read from the file
    except FileNotFoundError:
        print(f"Error: {RUN_FILE} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def setRUN(RUN_FILE, msg):
    try:
        with open(RUN_FILE, "w") as run:  # Open the file in write mode
            run.write(msg)  # Write the message to the file
            run.flush()  # Flush the buffer to ensure the message is written to the file
    except Exception as e:
        print(f"An error occurred while writing to {RUN_FILE}: {e}")

# Print the settings to the console
def print_settings():
    
    print("    SCAN SETTINGS")
    print("    -----------------------------------------------------")
    for key, value in settings["HVSCAN"].items():
        print(f"    {key}: {value}")
    
    print("\n    DETECTOR SETTINGS")
    print("    -----------------------------------------------------")
    for key, value in settings["DETECTOR"].items():
        print(f"    {key}: {value}")
    print("    -----------------------------------------------------")
    print("    -----------------------------------------------------\n")
    


# Write the settings to a file
def write_settings(file_path):
    with open(file_path, "w") as file:
        json.dump(settings, file, indent=4)
    # print(f"Settings have been written to {file_path}")

# Define a function to parse the arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Configure HV scan settings")

    # HVSCAN settings
    parser.add_argument('--scan_id', type=int, help="ID for the scan")
    parser.add_argument('--scan_type', type=str, choices=['current', 'daq'], default="daq", help="Type of scan: 'current' or 'daq' (default: 'daq')")
    parser.add_argument('--hveff_values', type=int, nargs='+', help="List of HV values (e.g., 2000 3000)")
    parser.add_argument('--max_trigger_values', type=int, nargs='+', help="Max trigger values for each HV point (e.g., 100 100)")
    
    # Optional parameters with default values
    parser.add_argument('--waiting_time', type=float, default=1, help="Waiting time ramping ends in mins (default: 1)")
    parser.add_argument('--measure_time', type=float, default=1, help="Measurement time in mins (default: 1)")
    parser.add_argument('--hv_end_flag', type=int, choices=[0, 1, 2], default=0, help="HV settings at the end (0: OFF, 1: Last HV value, 2: Standby) (default: 0)")
    parser.add_argument('--pt_flag', type=int, choices=[0, 1], default=1, help="Apply PT correction (0: without PT corr, 1: with PT corr)")

    return parser.parse_args()

# Function to format the execution time in HH:MM:SS
def format_execution_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{sec:02}"


if __name__ == '__main__':
    
    start_time = time.time()  # Start the timer

    text_kronos = """    
    -----------------------------------------------------
    -----------------------------------------------------
    
        W   W  EEEEE  L      CCCC  OOO  M   M  EEEEE    
        W   W  E      L     C     O   O MM MM  E
        W W W  EEEE   L     C     O   O M M M  EEEE
        WW WW  E      L     C     O   O M   M  E
        W   W  EEEEE  LLLLL  CCCC  OOO  M   M  EEEEE

            K   K  RRRR   OOO  N   N  OOO  SSSS       
            K  K   R   R O   O NN  N O   O S          
            KKK    RRRR  O   O N N N O   O  SSS        
            K  K   R  R  O   O N  NN O   O     S       
            K   K  R   R  OOO  N   N  OOO  SSSS      

    -----------------------------------------------------
    -----------------------------------------------------
    """

    print(text_kronos)

    RUN = ''
    measure_intval = 5 # sec

    """ Set CAEN environment variables
    CAENHV_BOARD_TYPE
    CAENHV_LINK_TYPE
    CAENHV_BOARD_ADDRESS
    CAENHV_USER (if set)
    CAENHV_PASSWORD (if set)
    RUN_FILE
    """
    # ip = "192.167.91.43" # CAEN Mainframe BARI
    ip = "90.147.203.174" # CAEN Mainframe INFN TORINO
    run_file = '/home/kronos/kronos/run/run'

    """ Set DETECTOR environment variables
    DETECTOR_NAME
    GAP/s_NAME/s
    GAP/s_SLOT/s
    GAP/s_CHANNEL/s
    DETECTOR_AREA (if)
    STANDBY_HV_VALUE
    """
    
    detector_name = "KRONOS-RPC"
    gap_name = ["TOP", "BOT"]
    gap_slot = [8, 8]
    gap_channel = [0, 2]
    standby_hv = 3000.

    """ Set HVSCAN environment variables
    SCAN_ID
    SCAN_TYPE
    HV_VALUES
    TRIGGER_VALUES (if)
    WAITING_TIME
    MEASURE_TIME
    HV_END_FLAG 
    """
    # scan_id = 2
    # scan_type = "daq" # current or daq
    # hveff_values = [200, 300]
    # max_trigger_values = [100, 100]
    # waiting_time = 0.1
    # measure_time = 0.1
    # hv_end_flag = 1 # flags values: 0 (switch OFF HV channels), 1 (leaves the channels with the last value setted), 2 (set all channels in standby value)

    # Set HVSCAN environment variables from parse function
    args = parse_arguments()
    scan_id = args.scan_id
    scan_type = args.scan_type
    hveff_values = args.hveff_values
    max_trigger_values = args.max_trigger_values
    waiting_time = args.waiting_time
    measure_time = args.measure_time
    hv_end_flag = args.hv_end_flag
    pt_flag = args.pt_flag


    # Create a dictionary to organize the settings
    settings = {
        "HVSCAN": {
            "scan_id": scan_id,
            "scan_type": scan_type,
            "hveff_values": hveff_values,
            "trigger_values": max_trigger_values,
            "waiting_time": waiting_time,
            "measure_time": measure_time,
            "hv_end_flag": hv_end_flag
        },
        "DETECTOR": {
            "detector_name": detector_name,
            "gap_name": gap_name,
            "gap_slot": gap_slot,
            "gap_channel": gap_channel,
            "standby_hv": standby_hv
        }

    }


    # Preparing the folders
    basedir = '/home/kronos/kronos/data/%06d/' % scan_id
    caen_dir = basedir + 'CAEN'
    daq_dir = basedir + 'DAQ'

    # Check if run ID exist already 
    if os.path.exists(basedir) and os.path.isdir(basedir):
        response = input(f"    Scan ID '{scan_id}' already exists. Do you want to continue \n    and overwrite it? (y/n): ").strip().lower()
        print("\n")
        if response != 'y':
            print("    Exiting KRONOS DAQ")
            exit()

    # Check scan settings
    if scan_type == 'daq':
        if len(hveff_values) != len(max_trigger_values):
            print("    ERROR: Please check scan settings")
            print("    Exiting KRONOS DAQ") 
            exit()



    # Log file
    log_file = basedir+"log.txt"
    log_message(log_file, "Starting HV Scan ID: %06d" % scan_id)

    # Init settigns
    print_settings()
    init_file = basedir+"init.json"
    write_settings(init_file)
    
    print("    HV SCAN ONGOING...")

    


    

    # with open(basedir+"log.txt", 'w') as file:
    #     file.write("Starting HV Scan ID: %06d\n" % scan_id)

    # print("Starting HV Scan ID: %06d" % scan_id)

    
    handle = connectCAEN(ip)
    if handle == 0:
        # print(f"Got handle: {handle}")
        # print(f"Comunication CAEN HV mainframe ----- OK")
        log_message(log_file, "Comunication CAEN HV mainframe: OK")
        
    else:
        # print(f"Comunication CAEN HV mainframe ----- ERROR")
        log_message(log_file, "Comunication CAEN HV mainframe: ERROR")
        
        sys.exit("Stopping the script")  # or use exit()





    # Loop over high voltage values
    for hv_index, hv_point in enumerate(hveff_values):

        print("    SCANNING HV %i ..." % (hv_index+1))
        
        # print("Scanning point HV: %i, %d V " % ((hv_index+1), hv_point))
        log_message(log_file, "Scanning point HV: %i, %d V " % ((hv_index+1), hv_point))
        setRUN(run_file,'INIT')



        basefilename = basedir + "/Scan%06d_HV%i" % (scan_id, (hv_index+1))
        filename_CAEN = basefilename + "_CAEN.root"
        filename_DAQ = basefilename + "_DAQ.root"

        # Create directories
        os.makedirs(basedir, exist_ok=True)
        os.makedirs(caen_dir, exist_ok=True)

        if scan_type == "daq":os.makedirs(daq_dir, exist_ok=True)



        # Creating histograms
        histos = []
        l = 0
        for index, name in enumerate(gap_name):

            # HVeff
            histname = 'HVeff_%s_%s' % (detector_name, name)
            histos.append(ROOT.TH1F(histname, histname, 1000, 0, 1))
            histos[l].SetCanExtend(ROOT.TH1.kAllAxes)
            l += 1


            # HVapp
            histname = 'HVapp_%s_%s' % (detector_name, name)
            histos.append(ROOT.TH1F(histname, histname, 1000, 0, 1))
            histos[l].SetCanExtend(ROOT.TH1.kAllAxes)
            l += 1

            # HVmon
            histname = 'HVmon_%s_%s' % (detector_name, name)
            histos.append(ROOT.TH1F(histname, histname, 1000, 0, 1))
            histos[l].SetCanExtend(ROOT.TH1.kAllAxes)
            l += 1

            # Imon
            histname = 'Imon_%s_%s' % (detector_name, name)
            histos.append(ROOT.TH1F(histname, histname, 1000, 0, 1))
            histos[l].SetCanExtend(ROOT.TH1.kAllAxes)
            l += 1








        # Turn channels on and set first voltage value 
        for index, name in enumerate(gap_name):
            slot = gap_slot[index]  
            channel = gap_channel[index]    
            hveff = hveff_values[hv_index]    

            #CAEN pars 'V0Set', 'I0Set', 'V1Set', 'I1Set', 'RUp', 'RDWn', 'Trip', 'SVMax', 'VMon', 'IMon', 'Status', 'Pw', 'POn', 'PDwn', 'TripInt', 'TripExt'
            
            # Turn the channel on
            set_channel_parameter(handle, slot, channel,'Pw', 1)

            # Set the voltage with PT correction
            if (pt_flag): set_channel_parameter(handle, slot, channel, 'V0Set', PTCorrection(hveff))  # Set voltage with correction
            else: set_channel_parameter(handle, slot, channel, 'V0Set', hveff)  # Set voltage with correction

        
        # Wait for ramping up to be completed (status = 1)
        ramping = 1
        while ramping == 1:
            # print("Channels still ramping")
            log_message(log_file, "Channels still ramping")
            time.sleep(10)  # Check every 10 seconds

            ramping = 0  # Assume not ramping unless we find a condition to keep it ramping

            for index, name in enumerate(gap_name):
                slot = gap_slot[index]  # Assuming row[1] is the slot number
                channel = gap_channel[index]    # Assuming row[0] is the channel number
                
                # Get the status from the CAEN device
                status = get_channel_parameter(handle, slot, channel, 'Status')

                # Check if the status indicates ramping (3 or 5)
                if status == 3 or status == 5:
                    ramping = 1
                    break
                else:
                    ramping = 0
        
        
        # Sleep for waiting time
        # print("Ramping completed, wait for waiting time...")
        log_message(log_file, "Ramping completed, wait for waiting time...")

        time.sleep(waiting_time*60)
        # print("Waiting time ended")
        log_message(log_file, "Waiting time ended")

        # Launch wavedump   
        if scan_type == 'daq': 

            # Define the directory path
            dir_ = basedir + "/HV%d_DIGITIZER/" % (hv_index+1)

            # If the directory doesn't exist, create it
            if not os.path.exists(dir_):
                os.makedirs(dir_)

            # Construct the command to run the digitizer
            command = "/home/kronos/kronos/digitizer/DIGITIZER_DAQ/src/wavedump %d %d %d > /dev/null 2>&1 &" % (max_trigger_values[hv_index], scan_id, hv_index+1)

            # Execute the command in the background using subprocess.Popen
            subprocess.Popen(command, shell=True)  

            time.sleep(10)

            setRUN(run_file, "START")

            



        # Run the scanning loop
        run = True
        p = 0
        while run:
            
            # Re-apply the voltage
            for index, name in enumerate(gap_name):
                slot = gap_slot[index]  
                channel = gap_channel[index]    
                hveff = hveff_values[hv_index]    

                if (pt_flag): set_channel_parameter(handle, slot, channel, 'V0Set', PTCorrection(hveff))  # Set voltage with correction
                else: set_channel_parameter(handle, slot, channel, 'V0Set', hveff)  # Set voltage with correction
            
            # Relax for a second before data taking
            time.sleep(1)

            


            l = 0
            for index, name in enumerate(gap_name):
                slot = gap_slot[index]  
                channel = gap_channel[index]
                hveff = hveff_values[hv_index]      

                # Filling histos
                # HVeff
                histos[l].Fill(hveff)
                l += 1
              
                # HVapp
                histos[l].Fill(get_channel_parameter(handle, slot, channel, 'V0Set'))
                l += 1

                # HVmon
                histos[l].Fill(get_channel_parameter(handle, slot, channel, 'VMon'))
                l += 1
                
                # Imon
                histos[l].Fill(get_channel_parameter(handle, slot, channel, 'IMon'))
                l += 1

            time.sleep(measure_intval)
            p += measure_intval
		
            # Re-set the run flag
            if scan_type != 'daq': # current scan

                if p < measure_time*60: run = 1
                else: run = 0

            elif scan_type == 'daq':
                
                readRUN(run_file)

                if RUN == "RUNNING": run = 1
                elif p < measure_time * 60: run = 1
                else: run = 0  # For any other message from DAQ



                 
                 

            

    
        # Open a ROOT file to save histograms
        outputFile = ROOT.TFile(filename_CAEN, "RECREATE")

        l = 0
        for index, name in enumerate(gap_name):
            slot = gap_slot[index]  
            channel = gap_channel[index]
            hveff = hveff_values[hv_index]      

            # Writing histos
            # HVeff
            histos[l].Write()
            l += 1
            
            # HVapp
            histos[l].Write()
            l += 1

            # HVmon
            histos[l].Write()
            l += 1
            
            # Imon
            histos[l].Write()
            l += 1

        # Close the ROOT file
        outputFile.Close()



        if scan_type == 'daq':
            
            # print("Send STOP command to DAQ!")
            log_message(log_file, "Send STOP command to DAQ!")
            setRUN(run_file,"STOP")
            time.sleep(2)
        
        print("    HV %i DONE" % (hv_index+1))



    if hv_end_flag == 0:
        for index, name in enumerate(gap_name):
            slot = gap_slot[index]  
            channel = gap_channel[index]      

            # Turn the channel OFF
            log_message(log_file, "Switching OFF all HV channels!")
            set_channel_parameter(handle, slot, channel,'Pw', 0)
    elif hv_end_flag == 1:
        log_message(log_file, "Keeping settings of all HV channels!")
        pass
    else:
        for index, name in enumerate(gap_name):
            slot = gap_slot[index]  
            channel = gap_channel[index]      

            # Turn the channel on
            set_channel_parameter(handle, slot, channel, 'V0Set', standby_hv)  # Set all channels with standby HV 
            log_message(log_file, "Setting STANDBY voltage in all HV channels!")


    # End the timer and print the execution time
    end_time = time.time()  # End the timer
    execution_time = end_time - start_time  # Calculate the execution time
    formatted_time = format_execution_time(execution_time)  # Format the time as HH:MM:SS

    # print("HVscan successfully ended!")
    log_message(log_file, "HVscan successfully ended!\n")

    print("    HVSCAN SUCCESSFULLY ENDED!!!")
    print("    Running time (HH:MM:SS): %s" % formatted_time)
    print("    -----------------------------------------------------")
    print("    -----------------------------------------------------\n")


























