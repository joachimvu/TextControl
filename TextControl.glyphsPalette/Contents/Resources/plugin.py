# encoding: utf-8

###########################################################################################################
#
#
# Palette Plugin
#
# Read the docs:
# https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Palette
#
#
###########################################################################################################
from __future__ import division, print_function, unicode_literals
import objc
from AppKit import NSColor, NSRect, NSBezierPath, NSPoint, NSSize
from GlyphsApp import *
from GlyphsApp.plugins import *
from vanilla import *
from math import tan, radians
import traceback

class TextControl (PalettePlugin):

  def settings(self):
    self.name = "Text Control"

    w = 160
    h = 210
    m = 10
    fh = 18
    yPos = 10
    self.w = Window((w, h))
    self.w.group = Group((0, 0, w, h))
    self.w.group.L = EditText( ( m, yPos, -(w/2)-(m/2), fh), placeholder="Left", sizeStyle="small")
    self.w.group.R = EditText( ( (w/2)+(m/2), yPos, -m, fh), placeholder="Right", sizeStyle="small")
    yPos += m/2+fh
    self.w.group.insertBtn = Button((m, yPos, -m, fh), "Insert", callback=self.insertGlyphs_, sizeStyle="small")
    yPos += m+fh
    self.w.group.sep = HorizontalLine((m, yPos, -m, 1))
    yPos += m
    self.w.group.search = EditText((m, yPos, -m, fh), placeholder="Search", sizeStyle="small", callback=self.editSearch_, continuous=True)
    yPos += m/2+fh
    self.w.group.replace = EditText((m, yPos, -m, fh), placeholder="Replace", sizeStyle="small")
    yPos += m/2+fh
    self.w.group.checkBox = CheckBox((m, yPos, -m, fh), "Show search matches", callback=self.checkBoxCallback_, value=True, sizeStyle="mini")
    yPos += m/2+fh
    self.w.group.replaceBtn = Button((m, yPos, -m, fh), "Replace", callback=self.replaceGlyphs_, sizeStyle="small")
    yPos += m+fh
    self.w.group.sep2 = HorizontalLine((m, yPos, -m, 1))
    yPos += m
    self.w.group.showAll = Button((m, yPos, -m, fh), "Show All Masters", callback=self.showAllMasters_, sizeStyle="small")

    self.dialog = self.w.group.getNSView()

  def __del__(self):
      Glyphs.removeCallback(self.insertGlyphs_)
      Glyphs.removeCallback(self.editSearch_)
      Glyphs.removeCallback(self.replaceGlyphs_)
      Glyphs.removeCallback(self.showAllMasters_)


#-------------#
# MAIN PLUGIN #
#-------------#

  @objc.python_method
  def get_layer_dict(self):
    # get dict of all layer sorted by selection status
    selected = Glyphs.font.selectedLayers
    total = Glyphs.font.currentTab.composedLayers
    cursorIdx = Glyphs.font.currentTab.layersCursor
    selecRange = Glyphs.font.currentTab.textRange
    before = total[:cursorIdx]
    after = total[cursorIdx+selecRange:]

    if selecRange > 0:
      return dict([("before",before),("selection",selected),("after",after)])
    else:
      return dict([("selection",total)])

  @objc.python_method
  def get_glyphNames(self,string,splitChar):
    return [x.strip() for x in string.split(splitChar)]

  @objc.python_method
  def get_layers_for_key(self, keyName):
    if keyName in self.get_layer_dict():
      return self.get_layer_dict()[keyName]
    else:
      return None

  @objc.python_method
  def process_tab_content(func):
    # processes the text change function's return values into the updated tab content
    def wrapper(self,sender):
      if Glyphs.font.currentTab:
        result = []
        if self.get_layers_for_key("before"):
          result.extend(self.get_layers_for_key("before"))
        if func(self,sender):
          result.extend(func(self,sender))
        else:
          result.extend(self.get_layers_for_key("selection"))
        if self.get_layers_for_key("after"):
          result.extend(self.get_layers_for_key("after"))
        Glyphs.font.currentTab.layers = result
        Glyphs.font.currentTab.textRange = 0
        self.w.group.search.set("")
        self.w.group.replace.set("")
    return wrapper

  @objc.python_method
  def get_glyphs(self,glyphsString,splitChar):
    # test inputs as viable glyph names
    if glyphsString:
      glyphNames = self.get_glyphNames(glyphsString,splitChar)
      testedGlyphNames = []
      for g in glyphNames:
        if g == "":
          continue
        else:
          try:
            Glyphs.font.glyphs[g].layers[0]
            testedGlyphNames.append(g)
          except AttributeError:
            Glyphs.showMacroWindow()
            print("%s is not a valid glyph name" % g)
            print(traceback.format_exc())
            return False
      return testedGlyphNames

  @objc.python_method
  def get_layers(self,glyphsList,masterId):
    for g in glyphsList:
      glyphToInsert = Glyphs.font.glyphs[g].layers[masterId]
      if glyphToInsert:
        yield glyphToInsert

  @process_tab_content
  def insertGlyphs_(self,sender):
    # insert a glyph left or right of each glyph from selection
    def insert_glyphs(source,inputL,inputR):
      for l in source:
        if inputL:
          for g in self.get_layers(inputL,l.layerId):
            yield g
        yield l
        if inputR:
          for g in self.get_layers(inputR,l.layerId):
            yield g

    glyphL = self.get_glyphs( self.w.group.L.get(), "/" )
    glyphR = self.get_glyphs( self.w.group.R.get(), "/" )

    result = list( insert_glyphs( self.get_layers_for_key("selection"), glyphL, glyphR ))
    return result

  @process_tab_content
  def replaceGlyphs_(self,sender):
    # search and replace function
    def replace_layers(source,search,replace):
      if search and replace:
        skipIndexes = []
        search_len = len(search)
        source_len = len(source)
        sourceNames = [l.parent.name for l in source]
        for i in range(source_len):
          if i not in skipIndexes:
            if sourceNames[i:i+search_len] == search:
              if replace:
                for g in list(self.get_layers(replace,source[i].associatedMasterId)):
                  yield g
              else:
                continue
              skipIndexes += range(i,i+search_len)
            else:
              yield source[i]

    source = self.get_layers_for_key("selection")
    glyphsFrom = [ self.get_glyphs(i, "/") for i in self.get_glyphNames( self.w.group.search.get(), ",") ]
    glyphsTo = [ self.get_glyphs(i, "/") for i in self.get_glyphNames( self.w.group.replace.get(), ",") ]
    result = None
    try:
      for i in range(len(glyphsFrom)):
        result = list( replace_layers( source, glyphsFrom[i], glyphsTo[i] ))
        source = result
    except IndexError:
      Glyphs.showMacroWindow()
      print("%s has no corresponding Replace input" % glyphsFrom[i])
      print(traceback.format_exc())
      return False

    try:
      Glyphs.removeCallback(self.draw_highlight)
      self.w.group.replaceBtn.setTitle( "Replace" )
    except:
      pass
    return result

  @process_tab_content
  def showAllMasters_(self,sender):
    # show all masters for selection
    def set_text(source):
      if "before" in self.get_layer_dict():
        yield GSControlLayer.newline()
      for master in Glyphs.font.masters:
        for l in source:
          if type(l) == GSControlLayer:
            yield l
          else:
            glyphToInsert = Glyphs.font.glyphs[l.parent.name]
            if glyphToInsert:
              yield glyphToInsert.layers[master.id]
        yield GSControlLayer.newline()

    result = list(set_text( self.get_layers_for_key("selection") ))
    return result


#-----------------------------#
# SEARCH MATCHES HIGHLIGHTING #
# all the drawing logic is separated from the actual plugin functionalities
# for debugging ease, might need some clean up
#-----------------------------#

  @objc.python_method
  def draw_highlight(self, layer, info):

    total = [l for l in Glyphs.font.currentTab.composedLayers]
    cursor = Glyphs.font.currentTab.layersCursor
    selecRange = Glyphs.font.currentTab.textRange

    searchList = [ self.get_glyphNames(i, "/") for i in self.get_glyphNames( self.w.group.search.get(), ",") ]

    def split_layers_by_line( layerList ):
      mainList = []
      subList = []
      for l in layerList:
        if l == GSControlLayer.newline():
          mainList.append(subList)
          subList = []
        else:
          subList.append(l)
      mainList.append(subList)
      return mainList

    def sum_kerns_up_to_idx(layerList,idx):
      prevLayer = None
      totalKerning = 0
      for i,l in enumerate(layerList):
        if i > 0:
          pair = Glyphs.font.kerningForPair(l.associatedMasterId, prevLayer.parent.rightKerningKey, l.parent.leftKerningKey)
          if "%s"%pair != "9.22337203685e+18" and pair:
            totalKerning += pair
        if i == idx-1:
          return totalKerning
        prevLayer = l

    def get_cursor():
      mainCounter = 0
      lineCounter = 0
      cursorDict = {}
      for line in split_layers_by_line( total ):
        subListWidths = [l.width for l in line]
        for i,y in enumerate(line):
          if cursor == mainCounter:
            cursorDict["line"] = lineCounter
            cursorDict["xOffset"] = sum(subListWidths[:i]) + sum_kerns_up_to_idx(line,i+1)
          mainCounter += 1
        mainCounter += 1
        lineCounter += 1
      return cursorDict

    def get_pos(searchList):
      mainCounter = 0
      lineCounter = 0
      for line in split_layers_by_line( total ):
        skipIndexes = []
        subListWidths = [l.width for l in line]
        subListNames = [l.parent.name for l in line]
        cursorLine = get_cursor()["line"]
        cursorOffset = get_cursor()["xOffset"]
        if searchList:
          search_len = len(searchList)
          for i in range(len(line)):
            if i not in skipIndexes:
              if searchList == subListNames[i:i+search_len]:
                if "EditView Line Height" in Glyphs.font.customParameters:
                  lineHeight = Glyphs.font.customParameters["EditView Line Height"]
                else:
                  lineHeight = (abs(l.master.descender)+l.master.ascender) + 200
                lineDiff = lineCounter - cursorLine
                yPos = -(lineDiff * lineHeight)
                xPos = -cursorOffset + sum( subListWidths[:i] ) + sum_kerns_up_to_idx(line,i+1)
                width = sum( subListWidths[ i:i+search_len ]) + sum_kerns_up_to_idx( line[ i:i+search_len ], search_len)
                yield dict([ 
                  ("x", xPos), 
                  ("y", yPos), 
                  ("xHeight", l.master.xHeight),
                  ("angle", l.master.italicAngle), 
                  ("descender", l.master.descender),
                  ("ascender", l.master.ascender), 
                  ("width", width),
                  ("idx", mainCounter) ])
                skipIndexes += range(i,i+search_len)
            mainCounter += 1
          lineCounter += 1

    def draw_bbox(x1, y1, x2, y2, x3, y3, x4, y4, outline=False):
        path = NSBezierPath.bezierPath()
        path.moveToPoint_((x1, y1))
        path.lineToPoint_((x2, y2))
        path.lineToPoint_((x3, y3))
        path.lineToPoint_((x4, y4))
        path.lineToPoint_((x1, y1))
        if not outline:
          path.fill()
        else:
          path.setLineWidth_(30)
          path.stroke()

    def ital(yPos):
      offset = tan(radians(angle)) * xHeight/2
      shift = tan(radians(angle)) * yPos - offset
      return shift

    def pick_color(option):
      return {
      0: (1, 0.99305, 0.561298, 0.6),
      1: (0.777493, 1, 0.972014, 0.6),
      2: (1, 0.877378, 0.980916, 0.6),
      3: (0.761078, 1, 0.783448, 0.6),
      4: (0.80931, 0.884228, 1, 0.6),
      }.get(option)

    c = 0
    matchNb = 0
    for s in searchList:
      for posDict in list(get_pos(s)):
        try:
          xPos = posDict["x"]
          yPos = posDict["y"]
          xHeight = posDict["xHeight"]
          angle = posDict["angle"]
          descender = posDict["descender"]
          ascender = posDict["ascender"]
          width = posDict["width"]
          idx = posDict["idx"]

          x1, y1 = xPos + ital(descender), yPos+ descender
          x2, y2 = xPos + ital(ascender), yPos + ascender
          x3, y3 = xPos + ital(ascender) + width, yPos + ascender
          x4, y4 = xPos + width + ital(descender), yPos + descender
          color = NSColor.colorWithRed_green_blue_alpha_(pick_color(c)[0], pick_color(c)[1], pick_color(c)[2], pick_color(c)[3]).set()

          if selecRange > 0:
            if idx < cursor-1 or idx > cursor-1 + selecRange-1:
              draw_bbox(x1, y1, x2, y2, x3, y3, x4, y4, outline= True)
            else:
              draw_bbox(x1, y1, x2, y2, x3, y3, x4, y4, outline= False)
              matchNb += 1
          else:
            draw_bbox(x1, y1, x2, y2, x3, y3, x4, y4, outline= False)
            matchNb += 1

        except:
          import traceback
          print(traceback.format_exc())
      c += 1
      if c > 4:
        c = 0

      if matchNb > 1:
        self.w.group.replaceBtn.setTitle( "Replace %s matches" % matchNb )
      elif matchNb == 1:
        self.w.group.replaceBtn.setTitle( "Replace 1 match" )
      else:
        self.w.group.replaceBtn.setTitle( "Replace" )

  def editSearch_(self,sender):
    if self.w.group.checkBox.get():
      try:
        Glyphs.removeCallback(self.draw_highlight)
        self.w.group.replaceBtn.setTitle( "Replace" )
      except:
        pass
      if sender.get() != "":
        Glyphs.addCallback(self.draw_highlight,DRAWBACKGROUND)

  def checkBoxCallback_(self,sender):
    if not sender.get():
      try:
        Glyphs.removeCallback(self.draw_highlight)
      except:
        pass
    else:
      Glyphs.addCallback(self.draw_highlight,DRAWBACKGROUND)



  @objc.python_method
  def __file__(self):
    """Please leave this method unchanged"""
    return __file__