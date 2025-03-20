# Digitizer_analysis
Analysis package for digitizer data taking (CAEN DT5742)


The master branch contains analysis tools used for efficiency studies. An example run is added with all relevant files.

Contents:

 - [Preparation ROOT files](#preparation-root-files)
 - [Configuration file](#configuration-file)
 - [Analyzer class](#analyzer-class)
 - [Analyze an efficiency run](#analyze-an-efficiency-run)
 

# Preparation ROOT files

Before running the analysis scripts, the raw data pulses (stored in txt files in the HVXX_DIGITIZER folder), are converted to ROOT file with its typical Tree structure. In order to do so, a script has been written which performes the conversion for all the HVpoints:

    txt2root.py
	
This script needs to be executed from the ROOT folder where the data is stored (i.e. the folder where the CAEN root files are stored). A single ROOT file per HVpoint is stored in the HVXX_DIGITIZER folder.




# Configuration file
 The config.py file contains the information of strips, digitizer mapping, gap names etc. It should closely follow the hardware configuration and the WebDCS settings. An overview of the settings is given below:
 
  - DIG_channels: list of digitizer channels connected to the strips. For DT5742, maximum 16 channels are available
  - DIG_strips: list of strips (ordered), one-to-one relation with DIG_channels
  - DIG_strips_mask: list of strips to be masked (dead or noisy)
  - stripArea: active strip area in cm2 (optional)
  - topGapName: top gap name, as given in the WebDCS
  - topGapName: bottom gap name, as given in the WebDCS
  


# Analyzer class
 This analyzerDigitizer.py class contains all the basic functionalities to analyze one single HVpoint. The analyzer is initialized by:
 
    import analyzerDigitizer as an
    analyzer = an.Analyzer(dir, saveDir, scanid, HVPoint, mode)
    analyzer.setVerbose(1) # verbosity, set to 1
    
    
with dir = the directory where the ROOT files are stored, saveDir a directory where all the output will be saved, scanid the scan ID number, HVPoint the current point to be analyzed and mode = efficieny/noise. A configuration from config.py (e.g. cfg_GRAPHITE) is loaded as follows:
 
    import config 
    analyzer.loadConfig(config.cfg_GRAPHITE)
    
Next, a set of analysis routines are called to perform the efficiency analysis.

To start, one can visualize all the pulses using the DQM function:

    analyzer.DQM()

The DQM function plots all pulses per event, from where it is possible to calibrate the trigger, determine the pulse time, etc.

In order to proceed with the efficiency analysis, the noise and muon time windows must be set, using:
    
    analyzer.setNoiseTimeWindow(startNoise, endNoise)
    analyzer.setMuonTimeWindow(startMuon, endMuon)
	
These numbers can be deduced by visualizing the pulses using the DQM function. The noise window is used to determine the mean noise offset (per channel) and the noise standard deviation. The muon time window is used to determine the hit efficiency: a pulse is considered as a hit if its amplitude is above an integer (n) times the noise standard deviation. Typically, this threshold n is 6 times the noise standard deviation and can be set as follows:

    analyzer.setThreshold(6)
	
An important parameter is the conversion of the digitized pulse to ns. This highly depends on the digitizer settings (stored in the ini file). Typically, at the highest sampling rate for the DT5742, one sample length equals 204.8 ps. This parameter is set as follows:
	
    analyzer.calibrateTime(0.2048) 
    # 5 GHz/MS:     0.2048     
    # 2.5 GHz/MS:   0.4096      
    # 1 GHz/MS:     0.1024
	
To run the analysis code looping over all events and channels per event, the following routine must be called:

    analyzer.analyze(False)

If the argument is True, the pulses are plotted zoomed in the muon time window, with visualisation of the threshold line (dashed blue).
        
All the input and output parameters are stored in a JSON file when calling:

    analyzer.write() 
	

# Analyze an efficiency run
 The script analyzeEfficiencyRun.py performs an efficiency analysis with a simple muon clusterization. The core analyzer is called for each HVpoint, and the currents, efficiency, cluster size and multiplicity are plotted as function of the HV. A Sigmoid fit is performed over the efficiency curve to extract the WP and all other relevant parameters. All parameters are stored in a JSON file.
 
 In order to run multiple analyses (e.g. with different thresholds), a tag must be given. All the data are then stored in a directory with the tag name.
 
 HOW TO USE:
 
 - download an efficiency run from the WebDCS, and extract the files to a directory;
 - adapt config.py, if necessary (or add a new config);
 - open analyzeEfficiencyRun.py, change the tag and config;
 - go to the extracted directory, and run the analyzeEfficiencyRun.py script.
 
