
import sys, os, glob, shutil, json, math, re, random
import ROOT
import analyzerDigitizer as an
import config

ROOT.gROOT.SetBatch()
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)


def atoi(text):
    return int(text) if text.isdigit() else text
def natural_keys(text):
    return [ atoi(c) for c in re.split('(\d+)',text) ]


def drawAux(c):

    textLeft = ROOT.TLatex()
    textLeft.SetTextFont(42)
    textLeft.SetTextSize(0.04)
    textLeft.SetNDC()
    textLeft.DrawLatex(c.GetLeftMargin(), 0.96, "#bf{RPC-BA} Laboratory,#scale[0.75]{ #it{Work in progress}}")

    textRight = ROOT.TLatex()
    textRight.SetNDC()
    textRight.SetTextFont(42)
    textRight.SetTextSize(0.04)
    textRight.SetTextAlign(31)
    textRight.DrawLatex(1.0-c.GetRightMargin(), 0.96, "S%d" % (scanid))

def setGraphStyle(g, xlabel, ylabel):

    g.SetLineWidth(2)
    g.SetLineColor(ROOT.kBlue)
    g.SetMarkerStyle(20)
    g.SetMarkerColor(ROOT.kBlue)
    g.GetXaxis().SetTitle(xlabel)
    g.GetYaxis().SetTitle(ylabel)
    g.GetYaxis().SetTitleOffset(1.8)
    g.GetYaxis().SetLabelOffset(2.0*g.GetYaxis().GetLabelOffset())
    g.GetXaxis().SetTitleOffset(1.2)
    g.GetXaxis().SetLabelOffset(2.0*g.GetXaxis().GetLabelOffset())

    return g



if __name__ == "__main__":

    scanid = int(sys.argv[1])


    ## tag: all the plots and results will be saved in a directory with its tagname
    tag = "ANALYSIS"

    chamber = "KRONOS-RPC"

    ## config: specify the configuration containing the mapping and strip dimensions (see config.py)
    cfg = config.KRONOS_RPC

    ## dir: ROOT directory of all raw data files 
    # dir = "/var/webdcs/HVSCAN/%06d/" % (scanid) 
    dir = "/home/kronos/kronos/data/%06d/" % (scanid)
    # dir = "/Users/dayron/GIF/test_beam_Oct2021/efficiency_scans/%06d/" % (scanid)

    ## xMin, xMax: typical voltage range for the analysis 
    xMin, xMax = 2000, 5000



    ##############################################################################################
    outputdir = "%s/%s/%s/" % (dir, tag, chamber)
    #if os.path.exists(outputdir): shutil.rmtree(outputdir) # delete output dir, if exists
    if not os.path.exists(outputdir):os.makedirs(outputdir) # make output dir


    HVeff = [] # storage of HV eff points
    out = {}



    # prepare TGraphs
    g_iMon_BOT = ROOT.TGraphErrors()
    g_iMon_TOP = ROOT.TGraphErrors()

    g_muon_cls = ROOT.TGraphErrors()

    # necessary to evaluate the error on the parameters at WP using linear interpolation
    g_muon_cls_err = ROOT.TGraphErrors()

    g_eff_muon = ROOT.TGraphErrors()
    g_eff_muon_err = ROOT.TGraphErrors()

    g_time_res = ROOT.TGraphErrors()

    iMonMax = -999

    # get the scan ID from the ROOT file
    files = glob.glob("%s/*CAEN.root" % dir)
    if len(files) == 0: sys.exit("No ROOT files in directory")
    scanid = int(re.findall(r'\d+', files[0])[0])

    # get all ROOT files in the dir
    files.sort(key=natural_keys) # sort on file name, i.e. according to HV points
    for i,CAENFile in enumerate(files):

        
        HVPoint = int(os.path.basename(CAENFile).split("_")[1][2:])
        # if HVPoint != 1: continue
        print ("Analyze HV point %d " % HVPoint)


        saveDir = outputdir + "HV%d/" % HVPoint
        if not os.path.exists(saveDir): os.makedirs(saveDir)

        analyzer = an.Analyzer(dir, saveDir, scanid, HVPoint, "efficiency")

        analyzer.loadConfig(cfg) # cfg_GIFPP cfg_FEB12
        analyzer.setVerbose(1)

        ### 2 PMT trigger on the chamber   #### comment the on eused for time resolution
        analyzer.setNoiseTimeWindow(5, 35) # analyzer.setNoiseTimeWindow(10, 60)  #  define start and end time of the noise window
        analyzer.setMuonTimeWindow(40, 60) # analyzer.setMuonTimeWindow(60, 90) #  define start and end time of the muon window

        ##### with aplifificatorre 
        # analyzer.setNoiseTimeWindow(10, 40)  # analyzer.setNoiseTimeWindow(10, 60) # define start and end time of the noise window
        # analyzer.setMuonTimeWindow(50, 90) # analyzer.setMuonTimeWindow(60, 90) # define start and end time of the muon window


        analyzer.setThreshold(4.) # set threshold, expressed as times noise stdv 



        # calibrate time from bits to ns, depending on digitizer sampling rate in the ini file
        # 5 GHz/MS:     0.2048     
        # 2.5 GHz/MS:   0.4096      
        # 1 GHz/MS:     0.1024
        analyzer.calibrateTime(0.2048)
        analyzer.DQM() # plot all events over entire time range 

        analyzer.analyze(True)
        analyzer.write()



        # load CAEN for HV and currents
        CAEN = ROOT.TFile(CAENFile)
        current_TOP = CAEN.Get("Imon_%s" % cfg['topGapName']).GetMean()
        current_BOT = CAEN.Get("Imon_%s" % cfg['botGapName']).GetMean()
        HV = CAEN.Get("HVeff_%s" % cfg['topGapName']).GetMean()
        if HV < 20: HV = CAEN.Get("HVeff_%s" % cfg['botGapName']).GetMean()
        HVeff.append(HV)

        if HV > xMax: xMax = HV
        if HV < xMin: xMin = HV

        CAEN.Close()


        # load analyzer results
        with open("%s/output.json" % (saveDir)) as f_in: analyzerResults = json.load(f_in)
        analyzerResults = analyzerResults['output_parameters']


        if current_BOT > iMonMax: iMonMax = current_BOT
        if current_TOP > iMonMax: iMonMax = current_TOP

        g_iMon_BOT.SetPoint(i, HV, current_BOT)
        g_iMon_TOP.SetPoint(i, HV, current_TOP)



        g_muon_cls.SetPoint(i, HV, analyzerResults['muonCLS'])
        g_muon_cls.SetPointError(i, 0, analyzerResults['muonCLS_err'])
        # g_muon_cls_err.SetPoint(i, 0, analyzerResults['muonCLS_err'])



        g_eff_muon.SetPoint(i, HV, 100.*analyzerResults['efficiencyAbs'])
        g_eff_muon.SetPointError(i, 0, 100.*analyzerResults['efficiencyAbs_err'])


        # if analyzerResults['resolutionTime'] > 0: 
        g_time_res.SetPoint(i, HV, analyzerResults['resolutionTime'])
        g_time_res.SetPointError(i, 0, analyzerResults['resolutionTime_err'])





    # do plotting and fitting
    c = ROOT.TCanvas("c1", "c1", 800, 800)
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.05)
    c.SetBottomMargin(0.1)

    params = ROOT.TLatex()
    params.SetTextFont(42)
    params.SetTextSize(0.03)
    params.SetNDC()




    ############################
    # muon efficiency + fit
    ############################ 
    c.Clear()
    g_eff_muon = setGraphStyle(g_eff_muon, "HV_{eff} (V)", "Efficiency (%)")
    g_eff_muon.GetYaxis().SetRangeUser(0,100)
    g_eff_muon.GetXaxis().SetRangeUser(xMin, xMax)
    g_eff_muon.SetLineWidth(2)
    g_eff_muon.SetLineColor(ROOT.kBlue)
    g_eff_muon.SetMarkerStyle(20)
    g_eff_muon.SetMarkerColor(ROOT.kBlue)
    g_eff_muon.Draw("ALP")

    sigmoid_HV50pct =          -1 # auto 
    sigmoid_lambda =           0.008
    sigmoid_emax =             0.98
    sigmoid_HVmin =            2000
    sigmoid_HVmax =            5000

    sigmoid = ROOT.TF1("sigmoid","[0]/(1+exp([1]*([2]-x)))", min(HVeff), max(HVeff));
    sigmoid.SetParName(0,"#epsilon_{max}");
    sigmoid.SetParName(1,"#lambda");
    sigmoid.SetParName(2,"HV_{50%}");
    sigmoid.SetParameter(0, sigmoid_emax);
    sigmoid.SetParameter(1, sigmoid_lambda);
    # sigmoid.SetParameter(2, sigmoid_HV50pct);   

    eff_ = 0
    if sigmoid_HV50pct < 0:
        HV_probe = sigmoid_HVmin
        sigmoid_HV50pct = -1

        while HV_probe <= sigmoid_HVmax:

            eff_ = g_eff_muon.Eval(HV_probe)

            if eff_ - 50 < 1 and -1 < eff_ - 50 :
                sigmoid_HV50pct = HV_probe
                break
            HV_probe += 1

    sigmoid.SetParameter(2, sigmoid_HV50pct)

    g_eff_muon.Fit("sigmoid", "E", "", sigmoid_HVmin, sigmoid_HVmax)

    fitted = g_eff_muon.GetFunction("sigmoid")
    emax = fitted.GetParameter(0)
    lam = fitted.GetParameter(1)
    hv50 = fitted.GetParameter(2)

    emax_err = fitted.GetParError(0)
    lam_err = fitted.GetParError(1)
    hv50_err = fitted.GetParError(2)



    WP = (math.log(19)/lam + hv50 + 150)
    dLambdaInverse = lam_err / (lam*lam) # error on 1/lambda
    WP_err = math.sqrt((math.log(19)*dLambdaInverse)*(math.log(19)*dLambdaInverse) + hv50_err*hv50_err) # total error on WP
    out["workingPoint"] = WP
    out["workingPoint_err"] = WP_err



    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.SetTextColor(1)
    latex.SetTextAlign(13)
    latex.DrawLatex(0.5, 0.5, "#epsilon_{max} = %.1f %%" % (fitted.GetParameter(0)))
    latex.DrawLatex(0.5, 0.45, "#lambda = %.3f" % fitted.GetParameter(1))
    latex.DrawLatex(0.5, 0.4, "HV_{50%%} = %.1f V" % fitted.GetParameter(2))
    latex.DrawLatex(0.5, 0.35, "WP = %.1f V" % WP)
    latex.DrawLatex(0.5, 0.3, "eff(WP) = %.1f %%" % (fitted.Eval(WP)))
    out["eff"] = fitted.Eval(WP)
    out["effMax"] = fitted.GetParameter(0)

    drawAux(c)
    c.SaveAs("%s/muonEfficiency.png" % outputdir)
    c.SaveAs("%s/muonEfficiency.pdf" % outputdir)
    c.SaveAs("%s/muonEfficiency.root" % outputdir)



    ############################
    # time resolution
    ############################ 
    c.Clear()
    g_time_res = setGraphStyle(g_time_res, "HV_{eff} (V)", "Time resolution (ps)")
    g_time_res.GetXaxis().SetRangeUser(xMin, xMax)
    g_time_res.GetYaxis().SetRangeUser(0., 1600.*1.1)
    g_time_res.SetLineWidth(2)
    g_time_res.SetLineColor(ROOT.kBlue)
    g_time_res.SetMarkerStyle(20)
    g_time_res.SetMarkerColor(ROOT.kBlue)
    g_time_res.Draw("ALP")

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.SetTextColor(1)
    latex.SetTextAlign(13)
    # latex.DrawLatex(0.5, 0.4, "WP = %.1f V" % WP)
    # latex.DrawLatex(0.5, 0.35, "timeRes(WP) = %.1f ps" % g_time_res.Eval(WP))
    params.DrawLatex(0.16, 0.9, "Time resolution at WP: %.1f ps" % g_time_res.Eval(WP))

    drawAux(c)
    c.SaveAs("%s/timeResolution.png" % outputdir)
    c.SaveAs("%s/timeResolution.pdf" % outputdir)
    c.SaveAs("%s/timeResolution.root" % outputdir)





    ############################
    # gap currents
    ############################
    c.Clear()
    g_iMon_BOT = setGraphStyle(g_iMon_BOT, "HV_{eff} (V)", "Current (#muA)")
    g_iMon_TOP = setGraphStyle(g_iMon_TOP, "HV_{eff} (V)", "Current (#muA)")

    g_iMon_BOT.Draw("ALP")
    g_iMon_BOT.GetYaxis().SetRangeUser(0, 1.1*iMonMax)

    g_iMon_TOP.SetLineColor(ROOT.kRed)
    g_iMon_TOP.SetMarkerColor(ROOT.kRed)
    g_iMon_TOP.Draw("SAME LP")

    params.DrawLatex(0.16, 0.9, "#color[4]{Current top gap at WP: %.2f #muA}" % g_iMon_TOP.Eval(WP))
    params.DrawLatex(0.16, 0.85, "#color[2]{Current bottom gap at WP: %.2f #muA}" % g_iMon_BOT.Eval(WP))
    params.DrawLatex(0.16, 0.8, "Total current at WP: %.2f #muA" % (g_iMon_BOT.Eval(WP)+g_iMon_TOP.Eval(WP)))
    out["iMonTop"] = g_iMon_TOP.Eval(WP)
    out["iMonBot"] = g_iMon_BOT.Eval(WP)
    out["iMonTot"] = (g_iMon_BOT.Eval(WP)+g_iMon_TOP.Eval(WP))
    drawAux(c)
    c.SaveAs("%s/gapCurrents.png" % outputdir)
    c.SaveAs("%s/gapCurrents.pdf" % outputdir)
    c.SaveAs("%s/gapCurrents.root" % outputdir)



    ############################
    # muon cluster size
    ############################
    c.Clear()
    g_muon_cls = setGraphStyle(g_muon_cls, "HV_{eff} (V)", "Muon cluster size")
    g_muon_cls.Draw("ALP")
    params.DrawLatex(0.16, 0.9, "Muon cluster size at WP: %.1f" % g_muon_cls.Eval(WP))
    out["muonCLS"] = g_muon_cls.Eval(WP)
    out["muonCLS_err"] = g_muon_cls_err.Eval(WP)
    drawAux(c)
    c.SaveAs("%s/muonCLS.png" % outputdir)
    c.SaveAs("%s/muonCLS.pdf" % outputdir)
    c.SaveAs("%s/muonCLS.root" % outputdir)



    with open("%s/results.json" % outputdir, 'w') as fp: json.dump(out, fp, indent=4)
                                                                   