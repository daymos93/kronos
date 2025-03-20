import sys, os, glob, shutil, json, math, re, random, array
import ROOT
import numpy as np
import heapq
from scipy.signal import find_peaks, find_peaks_cwt


ROOT.gROOT.SetBatch()
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)


class Analyzer():

    fIn = None  # pointer to ROOT file
    t = None    # raw data tree
    
    tag = ""
    savePath = ""
    dqmPath = "" 
    basePath = ""
    
    scanid = -1
    HVPoint = -1
    savedir = ""
    
    verbose = 0
    
    cfg = None
    
    stripArea = -1
    
    # threshold in integer number of noise sigma
    threshold = -1
    
    
    timeVector = array.array('d')
    muonTimeVector = array.array('d') # x-values for the muon time window
    
    # noise and muon time window definitions (in ns)
    noiseTimeWindowBegin = -1
    noiseTimeWindowEnd = -1
    
    muonTimeWindowBegin = -1
    muonTimeWindowEnd = -1
    
    noiseTimeWindowBeginIndex = -1
    noiseTimeWindowEndIndex = -1
    
    muonTimeWindowBeginIndex = -1
    muonTimeWindowEndIndex = -1
    

    
    # results from clusterization
    muonCLS = -1
    muonCLS_err = -1

    # results from efficiency
    efficiencyAbs = -1
    efficiencyAbs_err = -1
   
    
    
    # drawing options (see function __drawAux())
    c1 = None # default square canvas
    c2 = None # default rectangular canvas
    textCMS = "#bf{RPC-BA} Laboratory#scale[0.75]{ #it{work in progress}}" # CMS GIF++ TLatex (top left on canvas)
    textAux = None # auxiliary info (top right on canvas)
    

    def __init__(self, dir, savePath, scanid, HVPoint, scanType):

        self.scanid = scanid
        self.HVPoint = HVPoint
        self.basePath = dir
        self.savePath = savePath
        
        if not os.path.exists(self.savePath): os.makedirs(self.savePath)

        hvtoanalize = 5400
    
        # get the raw data
        # get the raw data
        self.fIn = ROOT.TFile("%s/HV%d_DIGITIZER/HV%d_DIGITIZER.root" % (dir, HVPoint, HVPoint))
        self.t = self.fIn.Get("data")



        # default square canvas
        self.c1 = ROOT.TCanvas("c1", "c1", 800, 800)
        self.c1.SetLeftMargin(0.12)
        self.c1.SetRightMargin(0.05)
        self.c1.SetTopMargin(0.05)
        self.c1.SetBottomMargin(0.1)
        
        # default rectangular canvas
        self.c2 = ROOT.TCanvas("c2", "c2", 900, 1200)
        self.c2.SetLeftMargin(0.12)
        self.c2.SetRightMargin(0.13)
        self.c2.SetTopMargin(0.05)
        self.c2.SetBottomMargin(0.1)
        
    def setVerbose(self, verbose):
    
        self.verbose = verbose
        
        
    def loadConfig(self, cfg):
    
        self.stripArea = cfg["stripArea"]   
        self.nStrips = len(cfg["DIG_channels"])
        
        self.DIG_strips = cfg["DIG_strips"]
        self.DIG_strips_mask = cfg["DIG_strips_mask"]
        self.DIG_channels = cfg["DIG_channels"]
 
    def setNoiseTimeWindow(self, start, end):
    
        self.noiseTimeWindowBegin = start
        self.noiseTimeWindowEnd = end
        
    def setMuonTimeWindow(self, start, end):
    
        self.muonTimeWindowBegin = start
        self.muonTimeWindowEnd = end
               
    def setThreshold(self, thrs):
    
        self.threshold = thrs

 
    def calibrateTime(self, sampling):
    
        time_ = self.fIn.Get("time")

        for t in time_: 
        
            t_ = t*sampling
            self.timeVector.append(t_)
            
            if self.noiseTimeWindowBeginIndex == -1 and t_ > self.noiseTimeWindowBegin: self.noiseTimeWindowBeginIndex = t
            if self.noiseTimeWindowEndIndex == -1 and t_ > self.noiseTimeWindowEnd: self.noiseTimeWindowEndIndex = t
            
            if self.muonTimeWindowBeginIndex == -1 and t_ > self.muonTimeWindowBegin: self.muonTimeWindowBeginIndex = t
            if self.muonTimeWindowEndIndex == -1 and t_ > self.muonTimeWindowEnd: self.muonTimeWindowEndIndex = t
            
            if t_ > self.muonTimeWindowBegin and t_ < self.muonTimeWindowEnd: self.muonTimeVector.append(t_)
       

       
        
    # convert DAC unit to VPP/2
    def DACtoV(self, pulse):

        #ret = ROOT.vector('double')()
        ret = array.array('d')
        for i in pulse: ret.append(1000.*(-.5 + i/4096.)) # conversion from DAC to -VPP/2 --> VPP/2
        return ret
        
       

       
    # performs a basic analysis on a single pulse: 
    #  - calculate the noise stdev and offset in noise window
    #  - substract noise offset from pulse
    #  - returns TGraph of pulse with correct timing axis (ns)
    def basePulseAnalysis(self, pulse, muonTimeWindow = True):
    
        # convert raw pulse from DAC to mV
        pulse = self.DACtoV(pulse)

        
        # calculate noise standard deviation and mean (in noise window)
        pulse_noise = array.array('d') # new pulse only in noise window
        for i,p in enumerate(pulse): 
        
            t_ = self.timeVector[i]
            if t_ < self.noiseTimeWindowBegin: continue
            if t_ > self.noiseTimeWindowEnd: break
            pulse_noise.append(p)

        noise_stdv = ROOT.TMath.RMS(len(pulse_noise), pulse_noise)
        noise_mean = ROOT.TMath.Mean(len(pulse_noise), pulse_noise) 

        
        # create new pulse, mean substracted
        pulse_muon = array.array('d')
        time_muon = array.array('d')
        it = 0 # tgraph iterator
        for i,p in enumerate(pulse): 
        
            t_ = self.timeVector[i]
            if muonTimeWindow:
                if t_ > self.muonTimeWindowBegin and t_ < self.muonTimeWindowEnd:                           
                    pulse_muon.append(p-noise_mean)
                    time_muon.append(t_)
                    it += 1
            else:
                pulse_muon.append(p-noise_mean)
                time_muon.append(t_)
                it += 1

        return pulse_muon, time_muon, noise_stdv
        
    def analyze(self, printPulses = False):
 
        print("Run analysis")
        
        nHitsAbs = 0
        nTrig = 0
        
        dir = self.savePath + "eventDisplay"
        #if os.path.exists(dir): shutil.rmtree(dir)
        if not os.path.exists(dir): os.makedirs(dir)
    
        pulses = [] # holding pointers to TTree
        graphs = [] # holding TGraphs per pulse per event, needs to be emptied after each event!
        g_ampl = [] # holding histogram for each channel for amplitude
        g_qint = [] # holding histogram for each channel for charge
        
        g_ampl_tot = ROOT.TH1D("ampl_tot", "Amplitude distribution", 450, 0, 150)
        # g_qint_tot = ROOT.TH1D("qint_tot", "Charge distribution", 300, -2, 4)  # range in tens exp
        g_qint_tot = ROOT.TH1D("qint_tot", "Charge distribution", 100000, 0, 1000000)
        
        
        for i, ch in enumerate(self.DIG_channels):
            
            print("Load digitizer channel %d" % ch)
            pulse = ROOT.vector('double')()
            pulses.append(pulse)
            self.t.SetBranchAddress("pulse_ch%d" % ch, pulses[i]) # , "pulse[1024]/F"
            
            h_ampl = ROOT.TH1D("ampl_ch%d" % ch, "Amplitude channel %d" % ch, 250, 0, 50)
            h_qint = ROOT.TH1D("qint_ch%d" % ch, "Charge channel %d" % ch, 250, 0, 50)
            g_ampl.append(h_ampl)
            g_qint.append(h_qint)
            
            

        # construct all histograms
        h_clustersize = ROOT.TH1D("clustersize", "Cluster size", 1000, 0, 1000)
        h_stripprofile = ROOT.TH1D("stripprofile", "Strip profile", 1000, 0, 1000)
        h_timeprofile = ROOT.TH2D("timeprofile", "Time profile", 25, 0, 5120, 1000, 0, 1000)  # bin circa 200 ps hardware limitation
        
        h_ToTprofile = ROOT.TH1D("ToTprofile", "ToT profile", 50, -1, 5)
        h_clusterprofile = ROOT.TH1D("clusterprofile", "Cluster profile", 1000, 0, 1000)

        h_clusterposition = ROOT.TH1D("clusterposition", "Cluster position", 1000, 0, 1000)

        h_chargeprofile = ROOT.TH2D("chargeprofile", "Charge profile", 1000, -500, 500, 1000, 0, 1000) 
        
        
        # loop over all events
        for evNum in range(0, self.t.GetEntries()+1):

            self.t.SetBranchStatus("pulse_TR_00", 0) # Disables the branch
            self.t.SetBranchStatus("pulse_TR_01", 0) # Disables the branch

            self.t.GetEntry(evNum) 
            nTrig += 1
            
            miny = 1e10
            maxy = -1e10
            
            thrs = [] # storage of all thresholds for each channel
            ampl = [] # storage of amplitudes (max amplitude) for each peak
            qint = [] # storage of charges (integral) for each peak
            qint_ch = [] # storage of charges (integral) for channel 
            jitter = [] # storage of time jitter for each peak
            time_init = [] # storage of time jitter for each peak
            channel = []
            cluster_channels = []
            ToT = [] # storage of time over threshold for each peak
            
            # qint_clus = []
            
            qclus = 0

            isEff = False
            
            # fill all TGraphs
            nHits_ = 0 # count # hits over trheshold
            for i, ch in enumerate(self.DIG_channels):
            
                pulse_muon, time_muon, noise_stdv = self.basePulseAnalysis(pulses[i])
                graph = ROOT.TGraph(len(time_muon), time_muon, pulse_muon)
                graph.SetName("g_%d" % ch)
                graphs.append(graph)
                
                thrs_ = -1.0*noise_stdv*self.threshold # compute threshold
                thrs.append(thrs_)
                
                if min(pulse_muon) < miny: miny = min(pulse_muon)
                if max(pulse_muon) > maxy: maxy = max(pulse_muon)
                
                isTriggered = (min(pulse_muon) < thrs_) # pulse is negative!
                
                # if isTriggered: nHits_ +=1
                
                ### peak analysis only if triggered 

                if isTriggered:

                    isEff = True

                    # peaks_number = self.count_peaks(pulse_muon, thrs_)
                    
                    pulse_muon_positive = array.array(pulse_muon.typecode, (x * -1 for x in pulse_muon))
                    thrs_positive = noise_stdv*self.threshold

                    peaks, prop = find_peaks(pulse_muon_positive, prominence=3)

                    if len(peaks) == 0: continue  # cosmic analysis
                    if len(peaks) > 2: continue  # cosmic analysis
                    
                    nHits_ +=1

                    cluster_channels.append(ch) # adding cluster channels 
                    qint_ch.append(0.)


                    for k, peak_min_idx in enumerate(peaks): ### peak analysis

                        #peak_min_idx = 0 # signal peak min index 
                        thr_left_idx = 0 # threshold left index
                        thr_right_idx = 0 # threshold right index
                        peak_init_idx = 0 # initial signal index
                        peak_end_idx = 0  # end signal signal index

                  
                        # finding singal thr indexes
                        Didx = 10

                        if min(pulse_muon[peak_min_idx-Didx:peak_min_idx], key=lambda x: abs(x - thrs_)):
                            thr_left_idx = pulse_muon.index(min(pulse_muon[peak_min_idx-Didx:peak_min_idx], key=lambda x: abs(x - thrs_))) # signal thr left index   # thr_left_idx = (np.abs(pulse_muon[prop["left_bases"][k]:peak_min_idx]) - thrs_).argmin()
                        else: thr_left_idx = peak_min_idx
                        
                        
                        thr_right_idx = pulse_muon.index(min(pulse_muon[peak_min_idx:peak_min_idx+Didx], key=lambda x: abs(x - thrs_)))
                        
                        # finding signal baseline indexes 

                        for j in range(thr_left_idx,0,-1): 
                            if noise_stdv > abs(pulse_muon[j]): break 
                            peak_init_idx = j

                        for j in range(thr_right_idx,len(pulse_muon)): 
                            if noise_stdv > abs(pulse_muon[j]): break 
                            peak_end_idx = j

                        # amplitude and charge analysis (only if strip is triggered)

                        g_ampl[i].Fill(-1.0*pulse_muon[peak_min_idx]) # convert to positive amplitude
                        g_ampl_tot.Fill(-1.0*pulse_muon[peak_min_idx])
                        
                        g_qint[i].Fill(-1.0*sum(pulse_muon[peak_init_idx:peak_end_idx])/50.) # integral of muon pulse  (in muon window)
                        
                        g_qint_tot.Fill(-1.0*sum(pulse_muon[peak_init_idx:peak_end_idx])*1000/50.) ### fC

                        # print(evNum, ch, k, len(peaks), time_muon[peak_init_idx], time_muon[peak_end_idx], -1.0*sum(pulse_muon[peak_init_idx:peak_end_idx])/50.)
                        
                        qint.append(-1.0*sum(pulse_muon[peak_init_idx:peak_end_idx])/50.)
                        
                        qint_ch[-1] = qint_ch[-1] + (-1.0)*sum(pulse_muon[peak_init_idx:peak_end_idx])/50. # sume all charge by peaks in the strip
                        
                        # qclus = qclus + sum(pulse_muon[peak_init_idx:peak_end_idx])/50.
                        

                        h_stripprofile.Fill(ch)
                        
                        #### timing analysis
                        jitter_ = time_muon[thr_left_idx] - time_muon[peak_init_idx]  # calculating jitter   

                        # to analyse all the strips fired
                        # if len(peaks) == 1 or (len(peaks) == 2 and k==0): # including only avalanche peaks
                        # h_timeprofile.Fill(jitter_,ch) 
                        jitter.append(jitter_)
                        channel.append(ch)
                        time_init.append(time_muon[peak_init_idx]) # storage of time jitter for each peak

                        # h_ToTprofile.Fill(time_muon[thr_right_idx]-time_muon[thr_left_idx])

            if isEff: 
                # to analyse only the fastest strip 
                if len(time_init) > 0: 
                    fastest_signal_idx = time_init.index(min(time_init))
                    if jitter[fastest_signal_idx] > 0: h_timeprofile.Fill(jitter[fastest_signal_idx]*1000.,channel[fastest_signal_idx])

                # analyzing charge profile
                if qint_ch:
                    # qint_ch_max_idx = qint_ch.index(max(qint_ch))
                    
                    pos, pos_mm = self.calculate_cluster_position(cluster_channels, qint_ch)

                    for kk in range(len(cluster_channels)): 

                        h_chargeprofile.Fill(cluster_channels[kk]-round(pos), qint_ch[kk]) # cluster_channels[qint_ch_max_idx], qint_ch[kk])
                        
                    if pos_mm > 0:     
                        h_clusterprofile.Fill(round(pos))
                        h_clusterposition.Fill(round(pos_mm))

           
            # if qclus !=0: 
                # g_qint_tot.Fill(qclus) # q in pC

            if miny < 0: miny_ = 1.1*miny
            else: miny_ = 0.9*miny
            
            if maxy > 0: maxy_ = 1.1*maxy
            else: maxy_ = 0.9*maxy

            
            if printPulses: self.plotEvent(graphs, dir, evNum, min(self.muonTimeVector), max(self.muonTimeVector), miny_, maxy_, thrs)
            
            if nHits_ > 0: 
            
                nHitsAbs += 1
                if nHits_ < 10: h_clustersize.Fill(nHits_) # simple clusterisation: just # strips triggered (no spatial/time constraint)

            
            # clean
            #for g in graphs: g.Delete()
            del graphs[:]

        print("Threshold mean: ", np.mean(thrs))
        self.meanThreshold = np.mean(thrs)
            
            
            
        self.efficiencyAbs = 1.0*nHitsAbs / (1.0*nTrig)
        self.efficiencyAbs_err = math.sqrt(self.efficiencyAbs*(1.0-self.efficiencyAbs)/nTrig)
        
        self.muonCLS = h_clustersize.GetMean()
        
        # plot DQM
        self.plotMuonCLS(h_clustersize)
        
        self.plotStripProfile(h_stripprofile)
        self.plotClusterProfile(h_clusterprofile)
        self.plotClusterPosition(h_clusterposition)
        
        self.plotTimeProfile(h_timeprofile)
        
        self.plotSingle(g_ampl_tot, 0, 150, "Amplitude (mV)", "amplitude")
        # self.plotSingle(g_qint_tot, 0, 1500, "Charge (a.u.)", "qint")

        self.plotCharge(g_qint_tot, 0, 9500, "Charge (fC)", "qint")
        # self.plotChannels(g_ampl, 0, 150, "Amplitude (mV)", "amplitude")
        # self.plotChannels(g_qint, 0, 150, "Charge (pC)", "qint")

        # self.plotToT(h_ToTprofile)

        self.plotChargeProfile(h_chargeprofile)
        




        
        
    def count_and_find_min_of_peaks(self ,waveform):
        peaks = []
        for i in range(1, len(waveform) - 1):
            # Check if current point is a peak (greater than its neighbors)
            if waveform[i] > waveform[i - 1] and waveform[i] > waveform[i + 1]:
                peaks.append(waveform[i])
        
        if peaks:
            min_peak_values = min(peaks)
            return len(peaks), min_peak_values
        else:
            return 0, None  # No peaks found





    
    def plotSingle(self, h, min_, max_, title, output):
    
      
        self.c1.cd()
        self.c1.Clear()

        if h.Integral() > 1: h.Scale(1.0/h.Integral())


        # self.c1.SetLogx()
            
        h.Draw("HIST")
        h.SetLineColor(ROOT.kBlue)

        h.GetYaxis().SetRangeUser(0, 1.3*h.GetMaximum())
        h.GetXaxis().SetRangeUser(min_, max_)
        h.SetLineWidth(2)  
            
        h.Draw("HIST SAME")
        h.SetLineWidth(2)  
        h.SetLineColor(ROOT.kBlue)

        h.GetXaxis().SetTitle(title)
        h.GetXaxis().SetTitleOffset(1.2)
        h.GetXaxis().SetLabelOffset(0.005)

        

        h.GetYaxis().SetTitle("Events (normalized)")   
        h.GetYaxis().SetTitleOffset(1.8)
        h.GetYaxis().SetLabelOffset(0.005)

        # h.Fit("gaus","","",min_,max_)
        self.c1.Update()
        self.__drawAux(self.c1)
        self.c1.RedrawAxis()
        self.c1.Modify()
        if self.verbose > 0:
            self.c1.SaveAs("%s%s.png" % (self.savePath, output))
            self.c1.SaveAs("%s%s.pdf" % (self.savePath, output))
            self.c1.SaveAs("%s%s.root" % (self.savePath, output))






    def plotCharge(self, h, min_, max_, title, output):
    
      
        self.c1.cd()
        self.c1.Clear()

        if h.Integral() > 1: h.Scale(1.0/h.Integral())


        # self.c1.SetLogx()
        
        # self.normalize_log_binning(h)

        # h.Rebin(2) # for low stats
            
        h.Draw("HIST")
        h.SetLineColor(ROOT.kBlue)

        h.GetYaxis().SetRangeUser(0, 1.3*h.GetMaximum())
        h.GetXaxis().SetRangeUser(min_, max_)
        h.SetLineWidth(2)  
            
        h.Draw("HIST SAME")
        h.SetLineWidth(2)  
        h.SetLineColor(ROOT.kBlue)

        h.GetXaxis().SetTitle(title)
        h.GetXaxis().SetTitleOffset(1.2)
        h.GetXaxis().SetLabelOffset(0.005)
        
        h.GetXaxis().SetMaxDigits(2)
        ROOT.TGaxis.SetExponentOffset(-0.02, -0.02, "x")

        

        h.GetYaxis().SetTitle("Events normalized / 10 fC")   
        h.GetYaxis().SetTitleOffset(1.8)
        h.GetYaxis().SetLabelOffset(0.005)

        params = ROOT.TLatex()
        params.SetTextFont(42)
        params.SetTextSize(0.03)
        params.SetNDC()
        # params.DrawLatex(0.16, 0.9, "Mean prompt charge: %.2f" % (h.GetMean()))

        ### Fiting profile
        if h.GetEntries() != 0:
            h.Fit("gaus","RE","",0, 2000)
            fitted = h.GetFunction("gaus")

            fitted.Draw("SAME")


            latex = ROOT.TLatex()
            latex.SetNDC()
            latex.SetTextFont(42)
            latex.SetTextSize(0.03)
            latex.SetTextAlign(13)
            latex.SetTextColor(4)
            latex.SetTextColor(ROOT.kBlack)
        
            
            latex.DrawLatex(0.16, 0.90, "Mean prompt charge: %.2f fC" % (fitted.GetParameter(1)))
            # latex.DrawLatex(0.16, 0.85, "sigma: %.2f" % fitted.GetParameter(2))

        self.c1.Update()
        self.__drawAux(self.c1)
        self.c1.RedrawAxis()
        self.c1.Modify()
        if self.verbose > 0:
            self.c1.SaveAs("%s%s.png" % (self.savePath, output))
            self.c1.SaveAs("%s%s.pdf" % (self.savePath, output))
            self.c1.SaveAs("%s%s.root" % (self.savePath, output))




    
    def plotChannels(self, hists, min_, max_, title, output):
    
        for i, ch in enumerate(self.DIG_channels):
            
            h = hists[i]
      
            self.c1.cd()
            self.c1.Clear()

            leg = ROOT.TLegend(.15, 0.75, .4, .93)
            leg.SetBorderSize(0)
            leg.SetTextSize(0.03)
            leg.SetFillStyle(0)
            
            if h.Integral() > 1: h.Scale(1.0/h.Integral())
            
            h.Draw("HIST")
            h.SetLineColor(ROOT.kBlue)
            h.GetYaxis().SetRangeUser(0, 1.3*h.GetMaximum())
            h.GetXaxis().SetRangeUser(min_, max_)
            h.SetLineWidth(2)  
            
            h.Draw("HIST SAME")
            h.SetLineWidth(2)  
            h.SetLineColor(ROOT.kBlue)

            h.GetXaxis().SetTitle(title)
            h.GetXaxis().SetTitleOffset(1.2)
            h.GetXaxis().SetLabelOffset(0.005)

            h.GetYaxis().SetTitle("Events (normalized)")   
            h.GetYaxis().SetTitleOffset(1.8)
            h.GetYaxis().SetLabelOffset(0.005)
            
            params = ROOT.TLatex()
            params.SetTextFont(42)
            params.SetTextSize(0.03)
            params.SetNDC()
            params.DrawLatex(0.16, 0.9, "Channel %d" % self.DIG_strips[i])
            

            self.__drawAux(self.c1)
            self.c1.RedrawAxis()
            self.c1.Modify()
            if self.verbose > 0:
                self.c1.SaveAs("%s%s_ch%d.png" % (self.savePath, output, self.DIG_strips[i])) 
                self.c1.SaveAs("%s%s_ch%d.pdf" % (self.savePath, output, self.DIG_strips[i])) 
                




    def find_min_values(self, waveform):
        minima = []
        for i in range(1, len(waveform) - 1):
            if waveform[i] < waveform[i - 1] and waveform[i] < waveform[i + 1]:
                minima.append(waveform[i])
        return minima





    def plotMuonCLS(self, h_clustersize):
    
        maxCLS = 8
  
        self.c1.cd()
        self.c1.Clear()

        leg = ROOT.TLegend(.15, 0.75, .4, .93)
        leg.SetBorderSize(0)
        leg.SetTextSize(0.03)
        leg.SetFillStyle(0)
        
        if h_clustersize.Integral() > 1: h_clustersize.Scale(1.0/h_clustersize.Integral())
        
        h_clustersize.Draw("HIST")
        h_clustersize.SetLineColor(ROOT.kBlue)
        h_clustersize.GetYaxis().SetRangeUser(0, 1.3*h_clustersize.GetMaximum())
        h_clustersize.GetXaxis().SetRangeUser(0, maxCLS)
        h_clustersize.SetLineWidth(2)  
        
        h_clustersize.Draw("HIST SAME")
        h_clustersize.SetLineWidth(2)  
        h_clustersize.SetLineColor(ROOT.kBlue)

        h_clustersize.GetXaxis().SetTitle("Cluster size")
        h_clustersize.GetXaxis().SetTitleOffset(1.2)
        h_clustersize.GetXaxis().SetLabelOffset(0.005)

        h_clustersize.GetYaxis().SetTitle("Events (normalized)")   
        h_clustersize.GetYaxis().SetTitleOffset(1.8)
        h_clustersize.GetYaxis().SetLabelOffset(0.005)
        
        params = ROOT.TLatex()
        params.SetTextFont(42)
        params.SetTextSize(0.03)
        params.SetNDC()
        params.DrawLatex(0.16, 0.9, "Mean muon cluster size (CLS): %.2f" % (self.muonCLS))
        

        self.__drawAux(self.c1)
        # self.drawChamber()
        self.c1.RedrawAxis()
        self.c1.Modify()
        if self.verbose > 0:
            self.c1.SaveAs("%sCLS_muon.png" % (self.savePath)) 
            self.c1.SaveAs("%sCLS_muon.pdf" % (self.savePath)) 
            self.c1.SaveAs("%sCLS_muon.root" % (self.savePath)) 





    def plotToT(self, h_ToTprofile):
    
        maxToT = 8
  
        self.c1.cd()
        self.c1.Clear()

        self.normalize_log_binning(h_ToTprofile)

        leg = ROOT.TLegend(.15, 0.75, .4, .93)
        leg.SetBorderSize(0)
        leg.SetTextSize(0.03)
        leg.SetFillStyle(0)
        
        if h_ToTprofile.Integral() > 1: h_ToTprofile.Scale(1.0/h_ToTprofile.Integral())
        
        h_ToTprofile.Draw("HIST")
        h_ToTprofile.SetLineColor(ROOT.kBlue)
        h_ToTprofile.GetYaxis().SetRangeUser(0, 1.3*h_ToTprofile.GetMaximum())
        # h_ToTprofile.GetXaxis().SetRangeUser(0, 2)
        h_ToTprofile.SetLineWidth(2)  
        
        h_ToTprofile.Draw("HIST SAME")
        h_ToTprofile.SetLineWidth(2)  
        h_ToTprofile.SetLineColor(ROOT.kBlue)

        h_ToTprofile.GetXaxis().SetTitle("ToT (ns)")
        h_ToTprofile.GetXaxis().SetTitleOffset(1.2)
        h_ToTprofile.GetXaxis().SetLabelOffset(0.005)

        h_ToTprofile.GetYaxis().SetTitle("Events (normalized)")   
        h_ToTprofile.GetYaxis().SetTitleOffset(1.8)
        h_ToTprofile.GetYaxis().SetLabelOffset(0.005)
        
        params = ROOT.TLatex()
        params.SetTextFont(42)
        params.SetTextSize(0.03)
        params.SetNDC()
        # params.DrawLatex(0.16, 0.9, "Mean Time over Threshold (ToT): %.2f" % (self.muonCLS))
        

        self.__drawAux(self.c1)
        # self.drawChamber()
        self.c1.RedrawAxis()
        self.c1.Modify()
        if self.verbose > 0:
            self.c1.SaveAs("%sToT_muon.png" % (self.savePath)) 
            self.c1.SaveAs("%sToT_muon.pdf" % (self.savePath)) 
            self.c1.SaveAs("%sToT_muon.root" % (self.savePath))   





    def plotStripProfile(self, h_stripprofile):
  
        self.c1.cd()
        self.c1.Clear()

        leg = ROOT.TLegend(.15, 0.75, .4, .93)
        leg.SetBorderSize(0)
        leg.SetTextSize(0.03)
        leg.SetFillStyle(0)
        
        h_stripprofile.Draw("HIST")
        h_stripprofile.SetLineColor(ROOT.kBlue)
        h_stripprofile.GetYaxis().SetRangeUser(0, 1.3*h_stripprofile.GetMaximum())
        h_stripprofile.GetXaxis().SetRangeUser(0, 16)
        h_stripprofile.SetLineWidth(2)  
        
        h_stripprofile.Draw("HIST SAME")
        h_stripprofile.SetLineWidth(2)  
        h_stripprofile.SetLineColor(ROOT.kBlue)

        h_stripprofile.GetXaxis().SetTitle("Strip number")
        h_stripprofile.GetXaxis().SetTitleOffset(1.2)
        h_stripprofile.GetXaxis().SetLabelOffset(0.005)

        h_stripprofile.GetYaxis().SetTitle("Number of hits")   
        h_stripprofile.GetYaxis().SetTitleOffset(1.8)
        h_stripprofile.GetYaxis().SetLabelOffset(0.005)
        
        # params = ROOT.TLatex()
        # params.SetTextFont(42)
        # params.SetTextSize(0.03)
        # params.SetNDC()
        # params.DrawLatex(0.16, 0.9, "Mean muon cluster size (CLS): %.2f" % (self.muonCLS))

        self.__drawAux(self.c1)
        self.c1.RedrawAxis()
        self.c1.Modify()
        if self.verbose > 0:
            self.c1.SaveAs("%sstrip_profile.png" % (self.savePath)) 
            self.c1.SaveAs("%sstrip_profile.pdf" % (self.savePath)) 
            self.c1.SaveAs("%sstrip_profile.root" % (self.savePath))  




    def plotClusterProfile(self, h_clusterprofile):
  
        self.c1.cd()
        self.c1.Clear()

        leg = ROOT.TLegend(.15, 0.75, .4, .93)
        leg.SetBorderSize(0)
        leg.SetTextSize(0.03)
        leg.SetFillStyle(0)
        
        h_clusterprofile.Draw("HIST")
        h_clusterprofile.SetLineColor(ROOT.kBlue)
        h_clusterprofile.GetYaxis().SetRangeUser(0, 1.3*h_clusterprofile.GetMaximum())
        h_clusterprofile.GetXaxis().SetRangeUser(0, 16)
        h_clusterprofile.SetLineWidth(2)  
        
        h_clusterprofile.Draw("HIST SAME")
        h_clusterprofile.SetLineWidth(2)  
        h_clusterprofile.SetLineColor(ROOT.kBlue)

        h_clusterprofile.GetXaxis().SetTitle("Strip number")
        h_clusterprofile.GetXaxis().SetTitleOffset(1.2)
        h_clusterprofile.GetXaxis().SetLabelOffset(0.005)

        h_clusterprofile.GetYaxis().SetTitle("Number of clusters")   
        h_clusterprofile.GetYaxis().SetTitleOffset(1.8)
        h_clusterprofile.GetYaxis().SetLabelOffset(0.005)


        ### Fiting profile

        if h_clusterprofile.GetEntries() != 0:
            h_clusterprofile.Fit("gaus","RE","",0, 16)
            fitted = h_clusterprofile.GetFunction("gaus")

            fitted.Draw("SAME")


            latex = ROOT.TLatex()
            latex.SetNDC()
            latex.SetTextFont(42)
            latex.SetTextSize(0.03)
            latex.SetTextAlign(13)
            latex.SetTextColor(4)
            latex.SetTextColor(ROOT.kBlack)
        
            
            latex.DrawLatex(0.16, 0.90, "mean (beam position): %.2f " % (fitted.GetParameter(1)))
            latex.DrawLatex(0.16, 0.85, "sigma: %.2f" % fitted.GetParameter(2))
            # latex.DrawLatex(0.25, 0.80, "FWHM: %.2f" % (2.355*fitted.GetParameter(2)))
            
            # params = ROOT.TLatex()
            # params.SetTextFont(42)
            # params.SetTextSize(0.03)
            # params.SetNDC()
            # params.DrawLatex(0.16, 0.9, "Mean muon cluster size (CLS): %.2f" % (self.muonCLS))

        self.__drawAux(self.c1)
        self.c1.RedrawAxis()
        self.c1.Modify()
        if self.verbose > 0:
            self.c1.SaveAs("%scluster_profile.png" % (self.savePath)) 
            self.c1.SaveAs("%scluster_profile.pdf" % (self.savePath)) 
            self.c1.SaveAs("%scluster_profile.root" % (self.savePath))   





    def plotClusterPosition(self, h_clusterposition):
  
        self.c1.cd()
        self.c1.Clear()

        leg = ROOT.TLegend(.15, 0.75, .4, .93)
        leg.SetBorderSize(0)
        leg.SetTextSize(0.03)
        leg.SetFillStyle(0)

        h_clusterposition.Rebin(3)
        
        h_clusterposition.Draw("HIST")
        h_clusterposition.SetLineColor(ROOT.kBlue)
        h_clusterposition.GetYaxis().SetRangeUser(0, 1.3*h_clusterposition.GetMaximum())
        h_clusterposition.GetXaxis().SetRangeUser(0, 16*6.5)
        h_clusterposition.SetLineWidth(2)  
        
        h_clusterposition.Draw("HIST SAME")
        h_clusterposition.SetLineWidth(2)  
        h_clusterposition.SetLineColor(ROOT.kBlue)

        h_clusterposition.GetXaxis().SetTitle("Position (mm)")
        h_clusterposition.GetXaxis().SetTitleOffset(1.2)
        h_clusterposition.GetXaxis().SetLabelOffset(0.005)

        h_clusterposition.GetYaxis().SetTitle("Number of clusters / 3.0 mm")   
        h_clusterposition.GetYaxis().SetTitleOffset(1.8)
        h_clusterposition.GetYaxis().SetLabelOffset(0.005)


        ### Fiting profile

        h_clusterposition.Fit("gaus","RE","",0, 1000)
        fitted = h_clusterposition.GetFunction("gaus")

        if fitted: fitted.Draw("SAME")


        latex = ROOT.TLatex()
        latex.SetNDC()
        latex.SetTextFont(42)
        latex.SetTextSize(0.03)
        latex.SetTextAlign(13)
        latex.SetTextColor(4)
        latex.SetTextColor(ROOT.kBlack)
       
        if h_clusterposition.GetEntries() != 0:
            latex.DrawLatex(0.16, 0.90, "mean: %.2f " % (fitted.GetParameter(1)))
            latex.DrawLatex(0.16, 0.85, "sigma: %.2f" % fitted.GetParameter(2))
            # latex.DrawLatex(0.25, 0.80, "FWHM: %.2f" % (2.355*fitted.GetParameter(2)))
        
        # params = ROOT.TLatex()
        # params.SetTextFont(42)
        # params.SetTextSize(0.03)
        # params.SetNDC()
        # params.DrawLatex(0.16, 0.9, "Mean muon cluster size (CLS): %.2f" % (self.muonCLS))

        self.__drawAux(self.c1)
        self.c1.RedrawAxis()
        self.c1.Modify()
        if self.verbose > 0:
            self.c1.SaveAs("%scluster_position.png" % (self.savePath)) 
            self.c1.SaveAs("%scluster_position.pdf" % (self.savePath)) 
            self.c1.SaveAs("%scluster_position.root" % (self.savePath))   





    def plotTimeProfile(self, h_timeprofile):
        
        self.c1.Clear()
        self.c1.Divide(1, 2)
        
        upperPad = ROOT.TPad("upperPad", "upperPad", 0.02, 0.2, 0.98, 1.)
        lowerPad = ROOT.TPad("lowerPad", "lowerPad", 0.02, 0., 0.98, 0.2)

        lowerPad.SetTopMargin(0.)
        upperPad.SetTopMargin(0.05)

        upperPad.Draw()		       
        lowerPad.Draw() 

        upperPad.cd()

        leg = ROOT.TLegend(.15, 0.75, .4, .93)
        leg.SetBorderSize(0)
        leg.SetTextSize(0.03)
        leg.SetFillStyle(0)
        
        h_timeprofile.Draw("COLZ")
        # h_timeprofile.SetLineColor(ROOT.kBlue)
        # h_timeprofile.GetXaxis().SetRangeUser(0, 20)#self.muonTimeWindowEnd - self.muonTimeWindowBegin) 
        h_timeprofile.GetYaxis().SetRangeUser(0, 16)
        h_timeprofile.GetXaxis().SetRangeUser(0, 5120)
        # h_timeprofile.SetLineWidth(2)  

        h_timeprofile.GetXaxis().SetTitle("Time (ps)")
        h_timeprofile.GetXaxis().SetTitleOffset(1.2)
        h_timeprofile.GetXaxis().SetLabelOffset(0.005)
        h_timeprofile.GetXaxis().SetLabelSize(0.035)
        h_timeprofile.GetXaxis().SetTitleSize(0.035)

        h_timeprofile.GetYaxis().SetTitle("Strip number")   
        h_timeprofile.GetYaxis().SetTitleOffset(1.2)
        h_timeprofile.GetYaxis().SetLabelOffset(0.005)
        h_timeprofile.GetYaxis().SetLabelSize(0.035)
        h_timeprofile.GetYaxis().SetTitleSize(0.035)
        
        self.__drawAux(self.c1)
        self.c1.RedrawAxis()
        self.c1.Modify()
        
        ################################
        # time profile projection + fit
        ################################ 

        lowerPad.cd()

        h_timeprofile_xproj = h_timeprofile.ProjectionX()
  
        # h_timeprofile_xproj.GetYaxis().SetTitle("Hits")   
        # h_timeprofile_xproj.GetYaxis().SetTitleOffset(1.2)
        # h_timeprofile_xproj.GetYaxis().SetLabelOffset(0.005)
        # h_timeprofile_xproj.GetYaxis().SetLabelSize(0.20)
        # h_timeprofile_xproj.GetYaxis().SetTitleSize(0.20)

        h_timeprofile_xproj.GetYaxis().SetLabelSize(0.)
        h_timeprofile_xproj.GetYaxis().SetTitleSize(0.)
        h_timeprofile_xproj.GetYaxis().SetTickLength(0.)

        h_timeprofile_xproj.GetXaxis().SetLabelSize(0.)
        h_timeprofile_xproj.GetXaxis().SetTitleSize(0.)
        # h_timeprofile_xproj.GetXaxis().SetTickLength(0.)
        
        h_timeprofile_xproj.Draw("HIST")
        
        # h_timeprofile_xproj.Fit("gaus","E","",0.,1.7)
        # fitted = h_timeprofile_xproj.GetFunction("gaus")

        if h_timeprofile_xproj.GetEntries() != 0:
            landauFit = ROOT.TF1("landauFit", "landau", 0., 1200.)
            landauFit.SetParLimits(1, 0, 500)  # Limitar el MPV en el rango [-5, 5]
            h_timeprofile_xproj.Fit("landauFit","RE") #, 2100.) # 2100 standard for all
            fitted = h_timeprofile_xproj.GetFunction("landauFit")

            # h_timeprofile_xproj.Fit("landau","RE","", 0., 2100.) #, 2100.) # 2100 standard for all
            # fitted = h_timeprofile_xproj.GetFunction("landau")
            
            fitted.Draw("SAME")

        latex = ROOT.TLatex()
        latex.SetNDC()
        latex.SetTextFont(42)
        latex.SetTextSize(0.13)
        latex.SetTextAlign(13)
        latex.SetTextColor(4)
        # latex.DrawLatex(0.55, 0.9, "Muon time window: %.2f ns" % (self.muonTimeWindowEnd-self.muonTimeWindowBegin))
        latex.SetTextColor(ROOT.kBlack)
        if h_timeprofile_xproj.GetEntries() != 0:
            latex.DrawLatex(0.55, 0.75, "MPV: %.2f ps" % (fitted.GetParameter(1)))
            latex.DrawLatex(0.55, 0.60, "sigma: %.3f ps" % fitted.GetParameter(2))

            self.resolutionTime = fitted.GetParameter(1)
            self.resolutionTime_err = math.sqrt(fitted.GetParError(1)*fitted.GetParError(1)+fitted.GetParameter(2)*fitted.GetParameter(2))
        else: self.resolutionTime = 0.; self.resolutionTime_err = 0.

        if self.verbose > 0:
            self.c1.SaveAs("%stime_profile.png" % (self.savePath)) 
            self.c1.SaveAs("%stime_profile.pdf" % (self.savePath))  
            self.c1.SaveAs("%stime_profile.root" % (self.savePath))  
            
        
            
    def find_n_min_values(self,waveform, n):
        return heapq.nsmallest(n, waveform)



    def plotChargeProfile(self, h_chargeprofile):
        
        self.c1.Clear()
        self.c1.Divide(1, 2)
        
        upperPad = ROOT.TPad("upperPad", "upperPad", 0.02, 0.2, 0.98, 1.)
        lowerPad = ROOT.TPad("lowerPad", "lowerPad", 0.02, 0., 0.98, 0.2)

        lowerPad.SetTopMargin(0.)
        upperPad.SetTopMargin(0.05)

        upperPad.Draw()		       
        lowerPad.Draw() 

        upperPad.cd()

        leg = ROOT.TLegend(.15, 0.75, .4, .93)
        leg.SetBorderSize(0)
        leg.SetTextSize(0.03)
        leg.SetFillStyle(0)
        
        h_chargeprofile.Draw("COLZ")
        h_chargeprofile.GetXaxis().SetRangeUser(-4, 5)
        h_chargeprofile.GetYaxis().SetRangeUser(0, 25*1.3) # h_chargeprofile.ProjectionX().GetMaximum()+100)

        h_chargeprofile.GetYaxis().SetTitle("Charge (pC)")
        h_chargeprofile.GetYaxis().SetTitleOffset(1.2)
        h_chargeprofile.GetYaxis().SetLabelOffset(0.005)
        h_chargeprofile.GetYaxis().SetLabelSize(0.035)
        h_chargeprofile.GetYaxis().SetTitleSize(0.035)

        h_chargeprofile.GetXaxis().SetTitle("Strips")   
        h_chargeprofile.GetXaxis().SetTitleOffset(1.2)
        h_chargeprofile.GetXaxis().SetLabelOffset(0.005)
        h_chargeprofile.GetXaxis().SetLabelSize(0.035)
        h_chargeprofile.GetXaxis().SetTitleSize(0.035)
        
        self.__drawAux(self.c1)
        self.c1.RedrawAxis()
        self.c1.Modify()
        
        ################################
        # charge profile projection + fit
        ################################ 

        lowerPad.cd()

        h_chargeprofile_xproj = h_chargeprofile.ProjectionX()
  
        # h_chargeprofile_xproj.GetYaxis().SetTitle("Hits")   
        # h_chargeprofile_xproj.GetYaxis().SetTitleOffset(1.2)
        # h_chargeprofile_xproj.GetYaxis().SetLabelOffset(0.005)
        # h_chargeprofile_xproj.GetYaxis().SetLabelSize(0.20)
        # h_chargeprofile_xproj.GetYaxis().SetTitleSize(0.20)

        h_chargeprofile_xproj.GetYaxis().SetLabelSize(0.)
        h_chargeprofile_xproj.GetYaxis().SetTitleSize(0.)
        h_chargeprofile_xproj.GetYaxis().SetTickLength(0.)

        h_chargeprofile_xproj.GetXaxis().SetLabelSize(0.)
        h_chargeprofile_xproj.GetXaxis().SetTitleSize(0.)
        # h_chargeprofile_xproj.GetXaxis().SetTickLength(0.)
        
        h_chargeprofile_xproj.Draw("HIST")
        
        if h_chargeprofile_xproj.GetEntries() != 0:
            h_chargeprofile_xproj.Fit("gaus","E","",-8, 8)
            fitted = h_chargeprofile_xproj.GetFunction("gaus")

            fitted.Draw("SAME")


        latex = ROOT.TLatex()
        latex.SetNDC()
        latex.SetTextFont(42)
        latex.SetTextSize(0.13)
        latex.SetTextAlign(13)
        latex.SetTextColor(4)
        latex.SetTextColor(ROOT.kBlack)
       
        if h_chargeprofile_xproj.GetEntries() != 0:
            latex.DrawLatex(0.65, 0.90, "mean: %.2f" % (fitted.GetParameter(1)))
            latex.DrawLatex(0.65, 0.75, "sigma: %.2f" % fitted.GetParameter(2))
            latex.DrawLatex(0.65, 0.60, "FWHM: %.2f" % (2.355*fitted.GetParameter(2)))


        if self.verbose > 0:
            self.c1.SaveAs("%scharge_profile.png" % (self.savePath)) 
            self.c1.SaveAs("%scharge_profile.pdf" % (self.savePath))  
            self.c1.SaveAs("%scharge_profile.root" % (self.savePath))  




    
    def plotEventDQM(self, graphs, outdir, evNum, minx, maxx, miny, maxy, thrs = []):

        # plot events on a divided canvas
        c = ROOT.TCanvas("evPlot", "c", 1600, 900)
        c.Divide(1, 18, 1e-5, 1e-5)
            
        thrs_lines = [] # hold all line objects

        # loop over all strips
        for i, ch in enumerate(list(self.DIG_channels)+[16,17]):
                
            c.cd(i+1)
            p = c.GetPad(i+1)
            p.SetGrid()
                
            p.SetTopMargin(0.25)
            p.SetBottomMargin(0.05)
            p.SetLeftMargin(0.07)
            p.SetRightMargin(0.05)

            g = graphs[i]
            

            g.SetMarkerStyle(20)
            g.SetMarkerSize(.4)
            g.SetLineWidth(1)
            g.SetLineColor(ROOT.kRed)
            g.SetMarkerColor(ROOT.kRed)

            g.GetYaxis().SetTitleFont(43)
            g.GetYaxis().SetTitleSize(12)
            g.GetYaxis().SetLabelFont(43)
            g.GetYaxis().SetLabelSize(20)
            g.GetYaxis().SetNdivisions(3)
            

            if minx != -1 and maxx != -1: g.GetXaxis().SetRangeUser(minx, maxx)
            if i > 15 and miny != -1 and maxy != -1: g.GetYaxis().SetRangeUser(-370., 150)
            if i < 16 and miny != -1 and maxy != -1: g.GetYaxis().SetRangeUser(miny, maxy)

            
                
            #g.GetXaxis().SetNdivisions(8)
            g.GetXaxis().SetLabelSize(0.15)
            g.GetXaxis().SetLabelOffset(-.9)
            if i%2  == 0: g.GetXaxis().SetLabelSize(0)

            


            g.SetLineWidth(2)
            g.Draw("AL") #AL AXIS X+
            graphs.append(g)


            right = ROOT.TLatex()
            right.SetNDC()
            right.SetTextFont(43)
            right.SetTextSize(20)
            right.SetTextAlign(13)
            if i < 16: right.DrawLatex(.97, .45,"#%d" % self.DIG_strips[i])
            else: right.DrawLatex(.97, .45,"tr0%d" % (i-16))
            
            if len(thrs) != 0:
            
                line = ROOT.TLine(minx, thrs[i], maxx, thrs[i]);
                line.SetLineColor(ROOT.kBlue)
                line.SetLineWidth(2)
                line.SetLineStyle(2)
                line.Draw()
                thrs_lines.append(line) # add to collector

            p.Update()
            p.Modify()
            c.Update()
                
                

        ### General text on canvas
        c.cd(0)

        

        # toptext
        right = ROOT.TLatex()
        right.SetNDC()
        right.SetTextFont(43)
        right.SetTextSize(20)
        right.SetTextAlign(23)
        right.DrawLatex(.5, .995, "Scan ID: %06d, %s, Event number: %06d  [x-axis: ns, y-axis: mV]" % (self.scanid, self.HVPoint, evNum))

        c.Modify()
            
        

        #c.SaveAs("%s/Scan%06d_HV%s_%d.pdf" % (outdir, self.scanid, self.HVPoint, evNum))
        c.SaveAs("%s/Scan%06d_HV%s_%d.png" % (outdir, self.scanid, self.HVPoint, evNum))               
    



        
    def DQM(self):
    
        print("Run DQM")
    
        pulses = [] # holding pointers to TTree
        graphs = [] # holding TGraphs per pulse per event, needs to be emptied after each event!
        
        dir = self.savePath + "DQM"
        #if os.path.exists(dir): shutil.rmtree(dir)
        if not os.path.exists(dir): os.makedirs(dir)
        
        # for i, ch in enumerate(self.DIG_channels):
        for i, ch in enumerate(list(self.DIG_channels)+[16,17]):
            
            print("Load digitizer channel %d" % ch)
            pulse = ROOT.vector('double')()
            pulses.append(pulse)
            if i < 16: self.t.SetBranchAddress("pulse_ch%d" % ch, pulses[i]) # , "pulse[1024]/F"
            else: self.t.SetBranchAddress("pulse_TR_0%d" % (ch-16), pulses[i]) # , "pulse[1024]/F"
            

        # loop over all events
        for evNum in range(0, self.t.GetEntries()+1):
        
            self.t.GetEntry(evNum)
            
            miny = 1e10
            maxy = -1e10
            
            # fill all TGraphs
            # for i, ch in enumerate(self.DIG_channels):
            for i, ch in enumerate(list(self.DIG_channels)+[16,17]):
                
                pulse_muon, time_muon, noise_stdv = self.basePulseAnalysis(pulses[i], False)
                graph = ROOT.TGraph(len(time_muon), time_muon, pulse_muon)
                graph.SetName("g_%d" % ch)
                graphs.append(graph)
            
                if i < 16:
                    if min(pulse_muon) < miny: miny = min(pulse_muon)
                    if max(pulse_muon) > maxy: maxy = max(pulse_muon)
            
                
            
            
            if miny < 0: miny_ = 1.1*miny
            else: miny_ = 0.9*miny
            
            if maxy > 0: maxy_ = 1.1*maxy
            else: maxy_ = 0.9*maxy
            
            self.plotEventDQM(graphs, dir, evNum, min(self.timeVector), max(self.timeVector), miny_, maxy_)

            del graphs[:]
        
        
        
    
        
    def __drawAux(self, c, aux = ""):
    
        textLeft = ROOT.TLatex()
        textLeft.SetTextFont(42)
        textLeft.SetTextSize(0.04)
        textLeft.SetNDC()
        textLeft.DrawLatex(c.GetLeftMargin(), 0.96, self.textCMS)

        
        textRight = ROOT.TLatex()
        textRight.SetNDC()
        textRight.SetTextFont(42)
        textRight.SetTextSize(0.04)
        textRight.SetTextAlign(31)
        if aux == "": textRight.DrawLatex(1.0-c.GetRightMargin(), 0.96, "S%d/HV%d" % (self.scanid, self.HVPoint))
        else: textRight.DrawLatex(1.0-c.GetRightMargin(), 0.96, "S%d/HV%d/%s" % (self.scanid, self.HVPoint, aux))

    def drawChamber(gasmix):
        latex = ROOT.TLatex()
        latex.SetNDC()
        latex.SetTextSize(0.04) 
        latex.DrawText(0.16,0.94,"RPC-BA")
        
        latex.SetTextFont(42)
        latex.SetTextSize(0.035) 
        # latex.DrawText(0.2,0.87,"BARI-1p0, "+gasmix)
        latex.DrawText(0.2,0.87,"KODEL-0p5, STD mixture")
        
        latex.SetTextFont(12)
        latex.SetTextSize(0.04) 
        latex.DrawText(0.28,0.94,"work in progress")



    def validateEvent(self):

        
        ## Quality flag validation (see Alexis: https://github.com/afagot/GIF_OfflineAnalysis/blob/master/src/utils.cc)
        qFlag = self.t.Quality_flag
        #print self.t.Quality_flag
        tmpflag = qFlag
        
        IsCorrupted = False
        nDigits = 0
        while tmpflag / int(math.pow(10, nDigits)) != 0: nDigits += 1;
        
        while not IsCorrupted and nDigits != 0:
        
            tdcflag = tmpflag / int(math.pow(10, nDigits-1))

            if tdcflag == 2: 
                IsCorrupted = True

            tmpflag = tmpflag % int(math.pow(10,nDigits-1))
            nDigits -= 1
        
        return not IsCorrupted
        

        ## PMT validation
        '''
        if len(self.TDC_channels_PMT) == 0: return True ## NO VALIDATION
        for ch in self.TDC_channels_PMT:
            if not ch in self.t.TDC_channel: return False
        
        return True ## default
        '''






    # Input: raw TDC channel/time vectors,
    # Output: converted TDC channels to strip numbers, within the optinally given time window
    def __groupAndOrder(self, TDC_CH, TDC_TS, windowStart = -1e9, windowEnd = 1e9):
    
        STRIP = []
        TS = []
        for i,ch in enumerate(TDC_CH):
            if not ch in self.TDC_channels: continue # only consider channels from chamber
            if TDC_TS[i] < windowStart: continue # min time window
            if TDC_TS[i] > windowEnd: continue # max time window
            #if TDC_TS[i] < self.timeWindowReject: continue # reject TDC first events
            #stripNo = cfg.TDC_strips[cfg.TDC_channels.index(ch)]
            stripNo = self.TDC_channels.index(ch)
            STRIP.append(stripNo)
            TS.append(TDC_TS[i])
        
        return STRIP, TS
 
            
            
    def count_peaks(self, waveform, threshold):
        peak_count = 0
        
        for i in range(1, len(waveform) - 1):
        
            if waveform[i] < threshold and waveform[i] < waveform[i - 1] and waveform[i] < waveform[i + 1]: peak_count += 1
        
        return peak_count

    # def normalize_log_binning(self, hist):
    #     # Loop over all bins
    #     for i in range(1, hist.GetNbinsX() + 1):  # ROOT bins are 1-indexed
    #         bin_content = hist.GetBinContent(i)
    #         bin_width = hist.GetBinWidth(i)

    #         # Normalize the bin content by the bin width
    #         if bin_width > 0:  # Avoid division by zero
    #             normalized_content = bin_content / bin_width
    #             hist.SetBinContent(i, normalized_content)






    def normalize_log_binning(self, hist):
        axis = hist.GetXaxis()
        bins = axis.GetNbins()

        from_val = axis.GetXmin()
        to_val = axis.GetXmax()
        width = (to_val - from_val) / bins
        new_bins = [ROOT.TMath.Power(10, from_val + i * width) for i in range(bins + 1)]

        axis.Set(bins, array.array('d', new_bins))  # Use array to convert to the appropriate C++ type





    def plotEvent(self, graphs, outdir, evNum, minx, maxx, miny, maxy, thrs = []):

        # plot events on a divided canvas
        c = ROOT.TCanvas("evPlot", "c", 1600, 900)
        c.Divide(1, 18, 1e-5, 1e-5)
            
        thrs_lines = [] # hold all line objects

        # loop over all strips
        for i, ch in enumerate(self.DIG_channels):
                
            c.cd(i+1)
            p = c.GetPad(i+1)
            p.SetGrid()
                
            p.SetTopMargin(0.25)
            p.SetBottomMargin(0.05)
            p.SetLeftMargin(0.07)
            p.SetRightMargin(0.05)

            g = graphs[i]
            

            g.SetMarkerStyle(20)
            g.SetMarkerSize(.4)
            g.SetLineWidth(1)
            g.SetLineColor(ROOT.kRed)
            g.SetMarkerColor(ROOT.kRed)

            g.GetYaxis().SetTitleFont(43)
            g.GetYaxis().SetTitleSize(12)
            g.GetYaxis().SetLabelFont(43)
            g.GetYaxis().SetLabelSize(20)
            g.GetYaxis().SetNdivisions(3)
            

            if minx != -1 and maxx != -1: g.GetXaxis().SetRangeUser(minx, maxx)
            if miny != -1 and maxy != -1: g.GetYaxis().SetRangeUser(miny, maxy)

            
                
            #g.GetXaxis().SetNdivisions(8)
            g.GetXaxis().SetLabelSize(0.15)
            g.GetXaxis().SetLabelOffset(-.9)
            if i%2  == 0: g.GetXaxis().SetLabelSize(0)

            


            g.SetLineWidth(2)
            g.Draw("AL") #AL AXIS X+
            graphs.append(g)


            right = ROOT.TLatex()
            right.SetNDC()
            right.SetTextFont(43)
            right.SetTextSize(20)
            right.SetTextAlign(13)
            right.DrawLatex(.97, .45,"#%d" % self.DIG_strips[i])
            
            if len(thrs) != 0:
            
                line = ROOT.TLine(minx, thrs[i], maxx, thrs[i]);
                line.SetLineColor(ROOT.kBlue)
                line.SetLineWidth(2)
                line.SetLineStyle(2)
                line.Draw()
                thrs_lines.append(line) # add to collector

            p.Update()
            p.Modify()
            c.Update()
                
                

        ### General text on canvas
        c.cd(0)

        

        # toptext
        right = ROOT.TLatex()
        right.SetNDC()
        right.SetTextFont(43)
        right.SetTextSize(20)
        right.SetTextAlign(23)
        right.DrawLatex(.5, .995, "Scan ID: %06d, %s, Event number: %06d  [x-axis: ns, y-axis: mV]" % (self.scanid, self.HVPoint, evNum))

        c.Modify()
            
        

        #c.SaveAs("%s/Scan%06d_HV%s_%d.pdf" % (outdir, self.scanid, self.HVPoint, evNum))
        c.SaveAs("%s/Scan%06d_HV%s_%d.png" % (outdir, self.scanid, self.HVPoint, evNum))




    def calculate_cluster_position(self, cluster, charge):
        # 16 ch, 104 mm --> pitch 6.5 mm && strip width 5.0 mm
        position = 0.
        pitch = 6.5 # mm
        
        position_mm = 0.

        if charge: 
        
            charge = np.array(charge)
            cluster= np.array(cluster)

            # Find the pixel with maximum intensity
            i_max = np.argmax(charge)

            # Include the pixel and its neighbors
            start = max(0, i_max - 1)  # Ensure we don't go out of bounds
            end = min(len(charge), i_max + 2)  # Include up to i_max + 1

            # Restrict to the region of interest
            charge_roi = charge[start:end]
            cluster_roi = cluster[start:end]


            # Calculate weighted centroid

            if np.sum(charge_roi) != 0.:
                # position = np.sum(cluster * charge) / np.sum(charge)
                position = np.sum(cluster_roi * charge_roi) / np.sum(charge_roi)

                position_mm = position*pitch

                # print(cluster, charge, position)
                # print(cluster*pitch, charge, position_mm)

        return position, position_mm





   
    def write(self):
    
        print("Write output JSON file")
        
        out = {}
        
        param_input = {

            "threshold"                 : self.threshold,
            
            "noiseTimeWindowBegin"      : self.noiseTimeWindowBegin,
            "noiseTimeWindowEnd"        : self.noiseTimeWindowEnd,
            
            "muonTimeWindowBegin"       : self.muonTimeWindowBegin,
            "muonTimeWindowEnd"         : self.muonTimeWindowEnd,
            
        }
        
        param_output = {

    
            "muonCLS"                   : self.muonCLS,
            "muonCLS_err"               : self.muonCLS_err,
    
            "efficiencyAbs"             : self.efficiencyAbs,
            "efficiencyAbs_err"         : self.efficiencyAbs_err,

            "resolutionTime"            : self.resolutionTime,
            "resolutionTime_err"        : self.resolutionTime_err,

            "meanThreshold"             : self.meanThreshold,

        }        
   
        data = {
        
            "input_parameters"          :  param_input, 
            "output_parameters"         :  param_output, 
        }
    
        with open("%soutput.json" % self.savePath, 'w') as fp: json.dump(data, fp, indent=4)

