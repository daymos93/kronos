from ROOT import THStack, TCanvas, TFile, gPad
class Plot(object):
 """Plot helper class
 """
 def __init__(self, *args): 
  """ The constructor. Possible arguments:
      1: fileName, histName - loads plot "histName" from file "fileName"
      2: plotList - list of Plot class instances. Merged into one plot
      3: plotList, True - list of Plot class instances. Combined using THStack
  """
  self.hist = None
  self.drawOpt = ""
  self.xAxisTitle = None
  self.yAxisTitle = None
  self.zAxisTitle = None 

  # Case 1: load the plot from the ROOT file 
  if len(args)==2 and type(args[0])==str and type(args[1])==str:
   fileName = args[0]
   histName = args[1]
   f = TFile.Open(fileName)
   if f:
    self.hist = f.Get(histName)
    self.hist.SetDirectory(0)
    print("Loaded histogram '{}' from file '{}'".format(histName,fileName))
 
  # case 2: list of plots gets added into a single plot
  elif len(args)==1 and type(args[0])==list and len(args[0])>0:
   plotList = args[0]
   self.hist = plotList[0].hist.Clone()
   for plot in plotList[1:]:
    self.hist.Add(plot.hist)
 
  # case 3: use THStack class to combine plots
  elif len(args)==2 and type(args[0])==list and type(args[1])==bool and args[1] and len(args[0])>0:
   plotList = args[0]
   self.hist = THStack()
   for plot in plotList:
    self.hist.Add(plot.hist)
    # copy other plot attributes (drawOpt, axis titles)
    self.drawOpt = plotList[0].drawOpt
    self.hist.SetTitle(plotList[0].hist.GetTitle())
    # for THStack, axis titles can only be set after the plot is drawn :-(
    self.xAxisTitle = plotList[0].hist.GetXaxis().GetTitle()
    self.yAxisTitle = plotList[0].hist.GetYaxis().GetTitle()
    self.zAxisTitle = plotList[0].hist.GetZaxis().GetTitle()

  # case 4: error
  else:
   raise RuntimeError("Cannot process input arguments '{}'".format(args))
 
 def setStyleSolid(self, color):
  """ Helper method to set style: solid histogram
  """
  if self.hist:
   self.hist.SetFillColor(color)
   self.hist.SetFillStyle(1001)
   self.hist.SetMarkerStyle(0)
   self.drawOpt = "hist"

 def setStyleMarker(self, color, marker = 20):
  """ Helper method to set style: marker with errorbars
  """
  if self.hist:
   self.hist.SetMarkerStyle(marker)
   self.hist.SetMarkerSize(1.)
   self.hist.SetMarkerColor(color)
   self.hist.SetLineColor(color)
   self.drawOpt = ""

 def setStyleErrorbar(self, color, fillPattern = 3345):
  """ Helper method to set style: errorbar
  """
  if self.hist:
   self.hist.SetFillColor(color)
   self.hist.SetFillStyle(fillPattern)
   self.hist.SetMarkerStyle(0)
   self.drawOpt = "E2"

 def draw(self, drawOpt = ""):
  self.hist.Draw("{} {}".format(self.drawOpt, drawOpt))
  # set axis titles if this is a THStack 
  if self.xAxisTitle: self.hist.GetXaxis().SetTitle(self.xAxisTitle)
  if self.yAxisTitle: self.hist.GetYaxis().SetTitle(self.yAxisTitle)
  if self.zAxisTitle: self.hist.GetZaxis().SetTitle(self.zAxisTitle)
  # we have to redraw axes
  gPad.RedrawAxis()