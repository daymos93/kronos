
import sys, os, glob, shutil, json, math, re, random
import ROOT
# from ROOT import gROOT
# from ROOT import TCanvas, TGraph, gPad, TF1,TF2, kRed, TMultiGraph, TLegend, gStyle, TPaveStats, TStyle, TLine, TText, TList, TLatex, TGraphErrors, TFormula, THStack


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
    textLeft.DrawLatex(c.GetLeftMargin(), 0.96, "#bf{RPC-BA} Laboratory#scale[0.75]{ #it{ preliminary}}") 

    # textRight = ROOT.TLatex()
    # textRight.SetNDC()
    # textRight.SetTextFont(42)
    # textRight.SetTextSize(0.04)
    # textRight.SetTextAlign(31)
    # textRight.DrawLatex(1.0-c.GetRightMargin(), 0.96, "S%d" % (scanid))

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextFont(42)
    latex.SetTextSize(0.035) 

    latex.DrawText(0.16, 0.9,"KODEL Double gap (0.5 mm)")

    latex.SetTextSize(0.03) 
    latex.DrawText(0.16, 0.85, "STD: TFE 95.2% + iC4H10 4.5% + SF6 0.3%") # "MIX500-2: TFE 96.5% + iC4H10 2.0% + SF6 1.5%")

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

    g.GetXaxis().SetNdivisions(705) 

    return g



if __name__ == "__main__":

    # scanid = int(sys.argv[1])
    
    ## CMS standard
    # scanid = [126, 126, 126, 126, 126, 126, 126, 126, 129, 129]
    # HVpoint = [1, 2, 3, 4, 5, 6, 7, 8, 1, 2]
    # HVeff = [2500, 3000, 3200, 3400, 3600, 3800, 4000, 4200, 4300, 4400] # storage of HV eff points

    scanid = [ 126, 126, 126, 126, 132, 126, 129, 129]
    HVpoint = [ 3, 4, 5, 6, 1, 8, 1, 2]
    HVeff = [ 3200, 3400, 3600, 3800, 4000, 4200, 4300, 4400] # storage of HV eff points

    ## MIX500-2
    # scanid = [134, 134, 134, 136]
    # HVpoint = [1, 2, 3, 1]
    # HVeff = [4000, 4200, 4400, 4500] # storage of HV eff points

    space= ","
    newline= " \n"	

    out = {}


    ## tag: all the plots and results will be saved in a directory with its tagname
    # tag = "Digitizer_efficiency"

    ## config: specify the configuration containing the mapping and strip dimensions (see config.py)
    cfg = config.KODEL_G0p5

    ## dir: ROOT directory of all raw data files 
    # dir = "/var/webdcs/HVSCAN/%06d/" % (scanid)

    ## xMin, xMax: typical voltage range for the analysis 
    xMin, xMax = 2000, 5000


    # ##############################################################################################
    outputdir = "/var/webdcs/ANALYSIS/dramos/KODEL_G0p5/plots/" # "%s/%s/" % (dir, tag)
    # #if os.path.exists(outputdir): shutil.rmtree(outputdir) # delete output dir, if exists
    # if not os.path.exists(outputdir):os.makedirs(outputdir) # make output dir

    # Dictionary to store data from each file
    data = {}

    # Loop through file names and load each JSON file
    for i in range(len(HVpoint)):
        # print(i)
        filepath = "/var/webdcs/HVSCAN/%06d/ANALYSIS/KODEL_G0p5/HV%i/output.json" % (scanid[i], HVpoint[i])
        
        with open(filepath, 'r') as file:
            data["HV%i" % (i+1)] = json.load(file)  # Key is the file name, value is the file's data

    # Print or work with the resulting dictionary
    # print(data['HV8']['output_parameters']['resolutionTime'])

    # HVeff = [2500, 3000, 3200, 3400, 3600, 3800, 4000, 4200, 4300] 
    out["HVeff"] = HVeff
    # prepare TGraphs
    # g_iMon_BOT = ROOT.TGraphErrors()
    # g_iMon_TOP = ROOT.TGraphErrors()

    g_muon_cls = ROOT.TGraphErrors()
    g_eff_muon = ROOT.TGraphErrors()
    g_time_res = ROOT.TGraphErrors()

    # necessary to evaluate the error on the parameters at WP using linear interpolation
    # g_muon_cls_err = ROOT.TGraphErrors()
    # g_eff_muon_err = ROOT.TGraphErrors()
    g_time_res_err = ROOT.TGraphErrors()

    for i in range(len(HVpoint)):
        g_muon_cls.SetPoint(i, HVeff[i], data["HV%i" % (i+1)]['output_parameters']['muonCLS'])
        g_muon_cls.SetPointError(i, 0, data["HV%i" % (i+1)]['output_parameters']['muonCLS_err'])
        # g_muon_cls_err.SetPoint(i, 0, data["HV%i" % (i+1)]['output_parameters']['muonCLS_err'])

        g_eff_muon.SetPoint(i, HVeff[i], 100.*data["HV%i" % (i+1)]['output_parameters']['efficiencyAbs'])
        g_eff_muon.SetPointError(i, 0, 100.*data["HV%i" % (i+1)]['output_parameters']['efficiencyAbs_err'])


        g_time_res.SetPoint(i, HVeff[i], data["HV%i" % (i+1)]['output_parameters']['resolutionTime'])
        g_time_res.SetPointError(i, 0, data["HV%i" % (i+1)]['output_parameters']['resolutionTime_err'])

        g_time_res_err.SetPoint(i, HVeff[i], data["HV%i" % (i+1)]['output_parameters']['resolutionTime_err'])



    # do plotting and fitting
    c = ROOT.TCanvas("c1", "c1", 800, 800)
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.05)
    c.SetBottomMargin(0.1)

    c.SetGridx()  # Enable grid on x-axis
    c.SetGridy()  # Enable grid on y-axis

    c.SetTickx(1)  # Ticks on top and bottom of the x-axis
    c.SetTicky(1) 

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
    sigmoid_emax =             1.
    sigmoid_HVmin =            2000
    sigmoid_HVmax =            5000
    sigmoid_psi =              0.3

    sigmoid = ROOT.TF1("sigmoid","[0]/(1+exp([1]*([2]-x)))", min(HVeff), max(HVeff))
    sigmoid.SetParName(0,"#epsilon_{max}")
    sigmoid.SetParName(1,"#lambda")
    sigmoid.SetParName(2,"HV_{50%}")
    sigmoid.SetParameter(0, sigmoid_emax)
    sigmoid.SetParameter(1, sigmoid_lambda)
    # sigmoid.SetParameter(2, sigmoid_HV50pct);  

    general = ROOT.TF1("general","[0]/((1+exp([1]*([2]-x)))**(1/[3]))", min(HVeff), max(HVeff))
    general.SetParName(0,"#epsilon_{max}")
    general.SetParName(1,"#lambda")
    general.SetParName(2,"HV_{50%}")
    general.SetParName(3,"#psi")

    general.SetParameter(0, sigmoid_emax)
    general.SetParameter(1, sigmoid_lambda)
    general.SetParameter(3, sigmoid_psi)

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
    general.SetParameter(2, sigmoid_HV50pct)

    # g_eff_muon.Fit("sigmoid", "E", "", sigmoid_HVmin, sigmoid_HVmax)

    # g_eff_muon.Fit("general", "E", "", 1000, 8000) # sigmoid_HVmin, sigmoid_HVmax)

    # fitted = g_eff_muon.GetFunction("sigmoid")
    # fitted = g_eff_muon.GetFunction("general")

    # emax = fitted.GetParameter(0)
    # lam = fitted.GetParameter(1)
    # hv50 = fitted.GetParameter(2)

    # emax_err = fitted.GetParError(0)
    # lam_err = fitted.GetParError(1)
    # hv50_err = fitted.GetParError(2)



    # WP = (math.log(19)/lam + hv50 + 150)
    # dLambdaInverse = lam_err / (lam*lam) # error on 1/lambda
    # WP_err = math.sqrt((math.log(19)*dLambdaInverse)*(math.log(19)*dLambdaInverse) + hv50_err*hv50_err) # total error on WP
    # out["workingPoint"] = WP
    # out["workingPoint_err"] = WP_err



    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.SetTextColor(1)
    latex.SetTextAlign(13)
    # latex.DrawLatex(0.5, 0.5, "#epsilon_{max} = %.1f %%" % (fitted.GetParameter(0)))
    # latex.DrawLatex(0.5, 0.45, "#lambda = %.3f" % fitted.GetParameter(1))
    # latex.DrawLatex(0.5, 0.4, "HV_{50%%} = %.1f V" % fitted.GetParameter(2))
    # latex.DrawLatex(0.5, 0.35, "WP = %.1f V" % WP)
    # latex.DrawLatex(0.5, 0.3, "eff(WP) = %.1f %%" % (fitted.Eval(WP)))
    # out["eff"] = fitted.Eval(WP)
    # out["effMax"] = fitted.GetParameter(0)

    drawAux(c)
    c.SaveAs("%s/muonEfficiency.png" % outputdir)
    c.SaveAs("%s/muonEfficiency.pdf" % outputdir)
    c.SaveAs("%s/muonEfficiency.root" % outputdir)



    ############################
    # time resolution
    ############################ 
    c.Clear()

    #removing not efficient points
    g_time_res_mod = ROOT.TGraphErrors()
    # for i in [2,4,5,6,8,9,10,11]: #range(2, g_time_res.GetN()):   # fro data with STD 
    #     x, y = g_time_res.GetPointX(i), g_time_res.GetPointY(i)
    #     g_time_res_mod.SetPoint(i - 2, x, y)  # Adjust index for new graph

    for i in range(g_time_res.GetN()):
        x, y = g_time_res.GetPointX(i), g_time_res.GetPointY(i)
        x_err, y_err = g_time_res.GetErrorX(i), g_time_res.GetErrorY(i)
        g_time_res_mod.SetPoint(i, x, y)  # Adjust index for new graph
        g_time_res_mod.SetPointError(i, x_err, y_err)  # Adjust index for new graph

    g_time_res_mod = setGraphStyle(g_time_res_mod, "HV_{eff} (V)", "Time resolution (ps)")
    g_time_res_mod.GetXaxis().SetRangeUser(3000, 4600)
    g_time_res_mod.GetYaxis().SetRangeUser(0., 800.*1.1)
    g_time_res_mod.SetLineWidth(2)
    g_time_res_mod.SetLineColor(ROOT.kBlue)
    g_time_res_mod.SetMarkerStyle(20)
    g_time_res_mod.SetMarkerColor(ROOT.kBlue)
    g_time_res_mod.Draw("AP")


    # latex = ROOT.TLatex()
    # latex.SetNDC()
    # latex.SetTextFont(42)
    # latex.SetTextSize(0.035) 

    # latex.DrawText(0.16, 0.9,"KODEL Double gap (0.5 mm)")
    # latex.DrawText(0.16, 0.85,"CMS Standard: TFE 95.2% + iC4H10 4.5% + SF6 0.3%")

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.035)
    latex.SetTextColor(1)
    latex.SetTextAlign(13)
    # latex.DrawLatex(0.5, 0.4, "WP = %.1f V" % WP)
    # latex.DrawLatex(0.5, 0.35, "timeRes(WP) = %.1f ps" % g_time_res.Eval(WP))
    # params.DrawText(0.16, 0.9,"Double gap (0.5 mm)")
    # params.DrawText(0.16, 0.9,"CMS Standard: TFE 95.2% + iC4H10 4.5% + SF6 0.3%")
    # params.DrawLatex(0.16, 0.80, "Time resolution at WP: %.0f (%.0f) ps" % (g_time_res_mod.Eval(WP), g_time_res_err.Eval(WP)) )
   

    drawAux(c)
    c.SaveAs("%s/timeResolution.png" % outputdir)
    c.SaveAs("%s/timeResolution.pdf" % outputdir)
    c.SaveAs("%s/timeResolution.root" % outputdir)


    ############################
    # muon cluster size
    ############################
    c.Clear()
    g_muon_cls = setGraphStyle(g_muon_cls, "HV_{eff} (V)", "Muon cluster size")
    g_muon_cls.Draw("ALP")
#    params.DrawLatex(0.16, 0.8, "Muon cluster size at WP: %.1f" % g_muon_cls.Eval(WP))
#    out["muonCLSWP"] = g_muon_cls.Eval(WP)
    # out["muonCLS_err"] = g_muon_cls_err.Eval(WP)
    drawAux(c)
    c.SaveAs("%s/muonCLS.png" % outputdir)
    c.SaveAs("%s/muonCLS.pdf" % outputdir)
    c.SaveAs("%s/muonCLS.root" % outputdir)


    ############################
    # efficiency + muon cluster size
    ############################
    c.Clear()
    c.SetTicky(0) 
    c.SetRightMargin(0.12)
    c.SetGridy(0)  # Enable grid on y-axis

    g_eff_muon.SetLineColor(ROOT.kBlue)
    g_eff_muon.SetMarkerColor(ROOT.kBlue)
    g_eff_muon.Draw("ALP")
    

    g_muon_cls_mod = ROOT.TGraphErrors()
    g_muon_cls_mod = setGraphStyle(g_muon_cls, "HV_{eff} (V)", "Muon cluster size")

    g_muon_cls_mod.SetLineColor(ROOT.kRed)
    g_muon_cls_mod.SetMarkerColor(ROOT.kRed)

    nfactor = (100./16.)
    for i in range(g_muon_cls.GetN()):

        x, y = g_muon_cls.GetPointX(i), g_muon_cls.GetPointY(i)*nfactor
        print(x,y)
        g_muon_cls_mod.SetPoint(i, x, y)  # Adjust index for new graph

    
    g_muon_cls_mod.Draw("P SAME")

    offset = 20.
    right_axis = ROOT.TGaxis(c.GetUxmax()+offset, 0, c.GetUxmax()+offset, 100, 0, 16, 515, "SL+")#, "+L")
    right_axis.SetLineColor(ROOT.kRed)  # Match the second graph's color
    right_axis.SetLabelColor(ROOT.kRed)
    right_axis.SetLabelFont(42)  # Default font
    right_axis.SetLabelSize(0.035)  # Default size
    right_axis.SetTitle("Muon cluster size")
    right_axis.SetTitleFont(42)  # Default font
    right_axis.SetTitleSize(0.035)  # Default size
    right_axis.SetTitleColor(ROOT.kRed)

    right_axis.SetTitleOffset(1.4)
    right_axis.SetLabelOffset(2.0*right_axis.GetLabelOffset())

    right_axis.Draw()

    # params.DrawLatex(0.16, 0.8, "#bf{WP:} %.0f V,  #bf{#varepsilon(WP):} %.1f" % (out["workingPoint"], out["eff"]) + " %") 
    # params.DrawLatex(0.16, 0.8, "#bf{WP:} %.0f V" % out["workingPoint"])
    # params.DrawLatex(0.16, 0.75, "#bf{Efficiency at WP:} %.1f " % out["eff"]+"%")
    # params.DrawLatex(0.16, 0.7, "#bf{CLS at WP:} %.1f" % (g_muon_cls_mod.Eval(WP)/nfactor))

    params.DrawLatex(0.16, 0.8, "#varepsilon_{max}: %.1f" % (g_eff_muon.Eval(HVeff[-1]))+ " %") 
    params.DrawLatex(0.16, 0.75, "CLS at #varepsilon_{max}: %.1f" % (g_muon_cls_mod.Eval(HVeff[-1])/nfactor)) 

#    out["muonCLSWP"] = g_muon_cls.Eval(WP)/nfactor
    # out["muonCLS_err"] = g_muon_cls_err.Eval(WP)
    drawAux(c)

    c.SaveAs("%s/muonEfficiencyCLS.png" % outputdir)
    c.SaveAs("%s/muonEfficiencyCLS.pdf" % outputdir)
    c.SaveAs("%s/muonEfficiencyCLS.root" % outputdir)


        


    ############################
    # efficiency + time resolution
    ############################
    c.Clear()
    c.SetTicky(0) 
    c.SetRightMargin(0.12)
    c.SetGridy()  # Enable grid on y-axis

    g_eff_muon.SetLineColor(ROOT.kBlack)
    g_eff_muon.SetMarkerColor(ROOT.kBlack)
    g_eff_muon.Draw("ALP")
    

    g_time_res_mod2 = ROOT.TGraphErrors()
    g_time_res_mod2 = setGraphStyle(g_time_res_mod, "HV_{eff} (V)", "Time resolution (ps)")
    
    right_axis_max = 999. #*1.1
    nfactor = (100./right_axis_max)
    for i in range(g_time_res_mod.GetN()):

        x, y = g_time_res_mod.GetPointX(i), g_time_res_mod.GetPointY(i)*nfactor # normalizing values
        x_err, y_err = g_time_res_mod.GetErrorX(i), g_time_res_mod.GetErrorY(i)*nfactor
        # print(x,y)
        g_time_res_mod2.SetPoint(i, x, y)  # Adjust index for new graph
        g_time_res_mod2.SetPointError(i, x_err, y_err)
    
    g_time_res_mod2.Draw("P SAME")

    offset = 0.
    right_axis = ROOT.TGaxis(c.GetUxmax()+offset, 0, c.GetUxmax()+offset, 100, 0, right_axis_max, 515, "SL+")#, "+L")
    right_axis.SetLineColor(4)  # Match the second graph's color
    right_axis.SetLabelColor(4)
    right_axis.SetLabelFont(42)  # Default font
    right_axis.SetLabelSize(0.035)  # Default size
    right_axis.SetTitle("Time resolution (ps)")
    right_axis.SetTitleFont(42)  # Default font
    right_axis.SetTitleSize(0.035)  # Default size
    right_axis.SetTitleColor(4)

    right_axis.SetTitleOffset(1.6)
    right_axis.SetLabelOffset(2.0*right_axis.GetLabelOffset())

    right_axis.Draw()

    # params.DrawLatex(0.16, 0.8, "#bf{WP:} %.0f V,  #bf{#varepsilon(WP):} %.1f" % (out["workingPoint"], out["eff"]) + " %") 
    # params.DrawLatex(0.16, 0.8, "#bf{WP:} %.0f V" % out["workingPoint"])
    # params.DrawLatex(0.16, 0.75, "#bf{Efficiency at WP:} %.1f " % out["eff"]+"%")
    # params.DrawLatex(0.16, 0.7, "#bf{Time resolution at WP:} %.0f (%.0f) ps" % (g_time_res_mod2.Eval(WP)/nfactor, g_time_res_err.Eval(WP)))

    # out["muonCLSWP"] = g_muon_cls.Eval(WP)/nfactor
    # out["muonCLS_err"] = g_muon_cls_err.Eval(WP)
    drawAux(c)

    c.SaveAs("%s/muonEfficiencytimeResolution.png" % outputdir)
    c.SaveAs("%s/muonEfficiencytimeResolution.pdf" % outputdir)
    c.SaveAs("%s/muonEfficiencytimeResolution.root" % outputdir)
 