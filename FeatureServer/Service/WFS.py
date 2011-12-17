__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: WFS.py 485 2008-05-18 10:51:09Z crschmidt $"

from FeatureServer.Service import Request
import vectorformats.Formats.WFS  

class WFS(Request):
    def encode(self, result):
        wfs = vectorformats.Formats.WFS.WFS(layername=self.datasource)
        results = wfs.encode(result)
        return ("text/xml", results)        
