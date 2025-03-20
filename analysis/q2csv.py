
import sys, os, glob, shutil, json, math, re, random
import ROOT
import numpy as np
# from ROOT import gROOT
# from ROOT import TCanvas, TGraph, gPad, TF1,TF2, kRed, TMultiGraph, TLegend, gStyle, TPaveStats, TStyle, TLine, TText, TList, TLatex, TGraphErrors, TFormula, THStack
# from root_numpy import root2array, array2tree, rec2array, fill_hist, hist2array

import analyzerDigitizer as an
import config

ROOT.gROOT.SetBatch()
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)
ROOT.gStyle.SetPalette(ROOT.kCividis)


def atoi(text):
    return int(text) if text.isdigit() else text
def natural_keys(text):
    return [ atoi(c) for c in re.split('(\d+)',text) ]


def drawAux(c):

    textLeft = ROOT.TLatex()
    textLeft.SetTextFont(42)
    textLeft.SetTextSize(0.04)
    textLeft.SetNDC()
    textLeft.DrawLatex(c.GetLeftMargin(), 0.96, "#bf{GIF++} #scale[0.75]{#it{preliminary}}")

    textRight = ROOT.TLatex()
    textRight.SetNDC()
    textRight.SetTextFont(42)
    textRight.SetTextSize(0.04)
    textRight.SetTextAlign(31)
    # textRight.DrawLatex(1.0-c.GetRightMargin(), 0.96, "S%d" % (scanid))

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextFont(42)
    latex.SetTextSize(0.035) 
    # latex.DrawText(0.2,0.87,"BARI-1p0, "+gasmix)
    latex.DrawText(c.GetLeftMargin()+0.45,0.9,"Single gap (1.0 mm)")

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

    space= ","
    newline= " \n"	


    ## tag: all the plots and results will be saved in a directory with its tagname
    tag = "Digitizer_efficiency"

    ## config: specify the configuration containing the mapping and strip dimensions (see config.py)
    cfg = config.BARI_1p0

    ## dir: ROOT directory of all raw data files 
    # dir = "/var/webdcs/HVSCAN/%06d/" % (scanid)
    dir = "/Users/dayron/GIF/test_beam_Oct2021/efficiency_scans/%06d/" % (scanid)

    ## xMin, xMax: typical voltage range for the analysis 
    xMin, xMax = 5000, 8000


    # ##############################################################################################
    outputdir = "%s/%s/" % (dir, tag)
    # #if os.path.exists(outputdir): shutil.rmtree(outputdir) # delete output dir, if exists
    # if not os.path.exists(outputdir):os.makedirs(outputdir) # make output dir

    name_csv_output = outputdir+"qh.csv"
    file_output=open(name_csv_output, "w")

    header= "q"+space+"f"+newline 
    file_output.write(header)


    HVeff = [] # storage of HV eff points
    h_qint = [] 
    h_ampl = [] 
    q = []
    q_err = []

    a = []
    a_err = []

    # out = {}

    # get the scan ID from the ROOT file
    files = glob.glob("%s/*CAEN.root" % dir)
    if len(files) == 0: sys.exit("No ROOT files in directory")
    scanid = int(re.findall(r'\d+', files[0])[0])

    # get all ROOT files in the dir
    files.sort(key=natural_keys) # sort on file name, i.e. according to HV points
    for i,CAENFile in enumerate(files):

        if i == 5: #HV5 - 6.kV
            HVPoint = int(os.path.basename(CAENFile).split("_")[1][2:])
            print ("Analyze HV point %d " % HVPoint)

            # load CAEN for HV and currents
            CAEN = ROOT.TFile(CAENFile)
            # current_TOP = CAEN.Get("Imon_%s" % cfg['topGapName']).GetMean()
            # current_BOT = CAEN.Get("Imon_%s" % cfg['botGapName']).GetMean()
            HV = CAEN.Get("HVeff_%s" % cfg['topGapName']).GetMean()
            if HV < 20: HV = CAEN.Get("HVeff_%s" % cfg['botGapName']).GetMean()
            HVeff.append(HV)

            if HV > xMax: xMax = HV
            if HV < xMin: xMin = HV

            CAEN.Close()


            # load qint ampl histo results
            qint = ROOT.TFile.Open("%s/%s/HV%s/qint.root" % (dir, tag, HVPoint), "READ")
            h_qint.append(qint.Get("c1").GetPrimitive("qint_tot"))
            nevents_q = qint.Get("c1").GetPrimitive("qint_tot").Integral()
            q.append(qint.Get("c1").GetPrimitive("qint_tot").GetMean())
            q_err.append(qint.Get("c1").GetPrimitive("qint_tot").GetStdDev()/(math.sqrt(nevents_q)))
            # print(nevents_q)

            for n in range(h_qint[0].GetNbinsX()):
                # print(h_qint[0].GetBinCenter(n), h_qint[0].GetBinContent(n))
                file_output.write(str(h_qint[0].GetBinCenter(n))+space+str((h_qint[0].GetBinContent(n))/nevents_q)+newline)

            file_output.close()
            



            
        
            ampl = ROOT.TFile.Open("%s/%s/HV%s/amplitude.root" % (dir, tag, HVPoint), "READ")
            h_ampl.append(ampl.Get("c1").GetPrimitive("ampl_tot")) 
            nevents_a = ampl.Get("c1").GetPrimitive("ampl_tot").Integral()
            a.append(ampl.Get("c1").GetPrimitive("ampl_tot").GetMean())
            a_err.append(ampl.Get("c1").GetPrimitive("ampl_tot").GetStdDev()/(math.sqrt(nevents_a)))
        # print(nevents_a)
         
    #     file_output.write(str(HV)+space+str(q[i])+space+str(q_err[i])+space+str(a[i])+space+str(a_err[i])+newline)

    # file_output.close()

    # do plotting and fitting
    c = ROOT.TCanvas("c1", "c1", 800, 800)

    c.cd(1)
    # ROOT.gPad.SetLogy()

    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.05)
    c.SetBottomMargin(0.1)
    
    # create a THStack
    # hs = ROOT.THStack("hs","qint_tot")
    
    lg = ROOT.TLegend(0.7,0.4,0.9,0.88)
    # lg = ROOT.TLegend(c.GetLeftMargin()+0.02,0.4,c.GetLeftMargin()+0.22,0.88)
    lg.SetBorderSize(0)
    lg.SetFillStyle(0)
    lg.SetTextSize(0.027)

    i=0
    # for h in [h_qint[0],h_qint[2],h_qint[5],h_qint[9]]: 
    for h in h_qint[:10]: 
        h.SetTitle(" ")
        h.GetXaxis().SetTitle("Muon charge (pC)")
        h.GetXaxis().SetTitleOffset(1.2)
        h.GetXaxis().SetLabelOffset(0.005)

        h.GetYaxis().SetTitle("Events")   
        h.GetYaxis().SetTitleOffset(1.8)
        h.GetYaxis().SetLabelOffset(0.005)

        # h.SetMaximum(h_qint[10].GetMaximum()*1.1)
        h.SetMaximum(1100)
        # h.SetMaximum(100)

        h.SetLineColor(i+40)
        # h.SetFillStyle(3001)
        # h.SetFillColor(i+40)

        if i == 0:
            h.Draw("HIST")
        else:
            h.Draw("HIST SAME")  

        # hs.Add(h)
        lg.AddEntry(h, "%s V" % str(HVeff[i]),"f")


        i=i+1


    # draw
    # hs.Draw("nostack")
    lg.Draw()
    drawAux(c)
    
    c.SaveAs("%s/hs_qint_6kV.png" % outputdir)
    c.SaveAs("%s/hs_qint_6kV.pdf" % outputdir)
    c.SaveAs("%s/hs_qint_6kV.root" % outputdir)

    c.Clear()

    c.cd(1)
    ROOT.gPad.SetLogy(0)

    i=0


    for h in h_ampl[:10]: 
        h.SetTitle(" ")
        h.GetXaxis().SetTitle("Signal amplitude (mV)")
        h.GetXaxis().SetTitleOffset(1.2)
        h.GetXaxis().SetLabelOffset(0.005)

        h.GetYaxis().SetTitle("Events")   
        h.GetYaxis().SetTitleOffset(1.8)
        h.GetYaxis().SetLabelOffset(0.005)

        h.SetMaximum(2200)

        h.SetLineColor(i+40)
        # h.SetFillStyle(3001)
        # h.SetFillColor(i+40)

        if i == 0:
            h.Draw("HIST")
        else:
            h.Draw("HIST SAME")  

        i=i+1


    lg.Draw()
    drawAux(c)

    c.SaveAs("%s/hs_ampl_6kV.png" % outputdir)
    c.SaveAs("%s/hs_ampl_6kV.pdf" % outputdir)
    c.SaveAs("%s/hs_ampl_6kV.root" % outputdir)
