__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: GeoJSON.py 483 2008-05-18 10:38:32Z crschmidt $"

from FeatureServer.Service import Request
from FeatureServer.Service import Action
from FeatureServer.Service import NoLayerException
from vectorformats.Feature import Feature
import vectorformats.Formats.GeoJSON 

try:
    import simplejson
except Exception, E:
    raise Exception("simplejson is required for using the JSON service. (Import failed: %s)" % E)

class GeoJSON(Request):
    def __init__(self, service):
        Request.__init__(self, service)
        self.callback = None
    
    def encode_metadata(self, action):
        layers = self.service.datasources
        metadata = []
        for key in layers.keys():
            metadata.append(
              { 
                'name': key,
                'url': "%s/%s" % (self.host, key)
              }
            )
            
        result_data = {'Layers': metadata}
        
        result = simplejson.dumps(result_data) 
        if self.callback:
            result = "%s(%s);" % (self.callback, result)
        
        return ("text/plain", result)
    
    def parse(self, params, path_info, host, post_data, request_method, format_obj=None):
        if 'callback' in params:
            self.callback = params['callback']
        g = vectorformats.Formats.GeoJSON.GeoJSON()
        Request.parse(self, params, path_info, host, post_data, request_method, format_obj=g)     
    
    def encode(self, result):
        g = vectorformats.Formats.GeoJSON.GeoJSON()
        result = g.encode(result)
        
        if self.datasource:
            datasource = self.service.datasources[self.datasource]
        
        if self.callback and datasource and hasattr(datasource, 'gaping_security_hole'):
            return ("text/plain", "%s(%s);" % (self.callback, result))
        else:    
            return ("text/plain", result)
    
