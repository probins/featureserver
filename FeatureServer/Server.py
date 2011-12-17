#!/usr/bin/python

__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: Server.py 607 2009-04-27 15:53:15Z crschmidt $"

import sys
import time
import os
import traceback
import ConfigParser
from web_request.handlers import wsgi, mod_python, cgi

import FeatureServer.Processing 

# First, check explicit FS_CONFIG env var
if 'FS_CONFIG' in os.environ:
    cfgfiles = os.environ['FS_CONFIG'].split(",")

# Otherwise, make some guesses.
else:
    # Windows doesn't always do the 'working directory' check correctly.
    if sys.platform == 'win32':
        workingdir = os.path.abspath(os.path.join(os.getcwd(), os.path.dirname(sys.argv[0])))
        cfgfiles = (os.path.join(workingdir, "featureserver.cfg"), os.path.join(workingdir,"..","featureserver.cfg"))
    else:
        cfgfiles = ("featureserver.cfg", os.path.join("..", "featureserver.cfg"), "/etc/featureserver.cfg")


class Server (object):
    """The server manages the datasource list, and does the management of
       request input/output.  Handlers convert their specific internal
       representation to the parameters that dispatchRequest is expecting,
       then pass off to dispatchRequest. dispatchRequest turns the input 
       parameters into a (content-type, response string) tuple, which the
       servers can then return to clients. It is possible to integrate 
       FeatureServer into another content-serving framework like Django by
       simply creating your own datasources (passed to the init function) 
       and calling the dispatchRequest method. The Server provides a classmethod
       to load datasources from a config file, which is the typical lightweight
       configuration method, but does use some amount of time at script startup.
       """ 
       
    def __init__ (self, datasources, metadata = {}, processes = {}):
        self.datasources   = datasources
        self.metadata      = metadata
        self.processes     = processes 
    
    def _loadFromSection (cls, config, section, module_type, **objargs):
        type  = config.get(section, "type")
        module = __import__("%s.%s" % (module_type, type), globals(), locals(), type)
        objclass = getattr(module, type)
        for opt in config.options(section):
            if opt != "type":
                objargs[opt] = config.get(section, opt)
        if module_type is 'DataSource':
            return objclass(section, **objargs)
        else:
            return objclass(**objargs)
    loadFromSection = classmethod(_loadFromSection)

    def _load (cls, *files):
        """Class method on Service class to load datasources
           and metadata from a configuration file."""
        config = ConfigParser.ConfigParser()
        config.read(files)
        
        metadata = {}
        if config.has_section("metadata"):
            for key in config.options("metadata"):
                metadata[key] = config.get("metadata", key)

        processes = {}
        datasources = {}
        for section in config.sections():
            if section == "metadata": continue
            if section.startswith("process_"):
                try:
                    processes[section[8:]] = FeatureServer.Processing.loadFromSection(config, section)
                except Exception, E:
                    pass 
            else:     
                datasources[section] = cls.loadFromSection(
                                        config, section, 'DataSource')

        return cls(datasources, metadata, processes)
    load = classmethod(_load)


    def dispatchRequest (self, base_path="", path_info="/", params={}, request_method = "GET", post_data = None,  accepts = ""):
        """Read in request data, and return a (content-type, response string) tuple. May
           raise an exception, which should be returned as a 500 error to the user."""  
        response_code = "200 OK"
        host = base_path
        request = None
        content_types = {
          'application/vnd.google-earth.kml+xml': 'KML',
          'application/json': 'GeoJSON',
          'text/javascript': 'GeoJSON',
          'application/rss+xml': 'GeoRSS',
          'text/html': 'HTML',
          'osm': 'OSM',
          'gml': 'WFS',
          'wfs': 'WFS',
          'kml': 'KML',
          'json': 'GeoJSON',
          'georss': 'GeoRSS',
          'atom': 'GeoRSS',
          'html': 'HTML',
          'geojson':'GeoJSON'
        }  
        
        path = path_info.split("/")
        
        found = False
        
        format = ""
        
        if params.has_key("format"):
            format = params['format']
            if format.lower() in content_types:
                format = content_types[format.lower()]
                found = True
        
        if not found and len(path) > 1:
            path_pieces = path[-1].split(".")
            if len(path_pieces) > 1:
                format = path_pieces[-1]
                if format.lower() in content_types:
                    format = content_types[format.lower()]
                    found = True
        
        if not found and accepts:
           if accepts.lower() in content_types:
               format = content_types[accepts.lower()]
               found = True
        
        if not found and not format:
            if self.metadata.has_key("default_service"):
                format = self.metadata['default_service']
            else:    
                format = "GeoJSON"
                
        service_module = __import__("Service.%s" % format, globals(), locals(), format)
        service = getattr(service_module, format)
        request = service(self)
            
        response = []
        
        request.parse(params, path_info, host, post_data, request_method)
        
        # short circuit datasource where the first action is a metadata request. 
        if len(request.actions) and request.actions[0].method == "metadata": 
            return request.encode_metadata(request.actions[0])
        
        datasource = self.datasources[request.datasource] 
        
        if request_method != "GET" and hasattr(datasource, 'processes'):
            raise Exception("You can't post data to a processed layer.") 

        
        datasource.begin()
        try:
            for action in request.actions:
                method = getattr(datasource, action.method)
                result = method(action)
                response += result 
            datasource.commit()
        except:
            datasource.rollback()
            raise
        
        if hasattr(datasource, 'processes'):
            for process in datasource.processes.split(","):
                if not self.processes.has_key(process): 
                    raise Exception("Process %s configured incorrectly. Possible processes: \n\n%s" % (process, ",".join(self.processes.keys() ))) 
                response = self.processes[process].dispatch(features=response, params=params)

        mime, data = request.encode(response)
        data = data.encode("utf-8") 
        return (mime, data)

theServer = None
lastRead = 0

def handler (apacheReq):
    global theServer
    if not theServer:
        options = apacheReq.get_options()
        cfgs    = cfgfiles
        if options.has_key("FeatureServerConfig"):
            cfgs = (options["FeatureServerConfig"],) + cfgs
        theServer = Server.load(*cfgs)
    return mod_python(theServer.dispatchRequest, apacheReq)

def wsgi_app (environ, start_response):
    global theServer, lastRead
    last = 0
    for cfg in cfgfiles:
        try:
            cfgTime = os.stat(cfg)[8]
            if cfgTime > last:
                last = cfgTime
        except:
            pass        
    if not theServer or last > lastRead:
        cfgs      = cfgfiles
        theServer = Server.load(*cfgs)
        lastRead = time.time()
        
    return wsgi(theServer.dispatchRequest, environ, start_response)


if __name__ == '__main__':
    service = Server.load(*cfgfiles)
    cgi(service)
