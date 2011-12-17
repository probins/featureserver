__author__  = "MetaCarta"
__copyright__ = "Copyright (c) 2006-2008 MetaCarta"
__license__ = "Clear BSD" 
__version__ = "$Id: __init__.py 614 2009-09-16 01:50:40Z jlivni $"

from web_request.handlers import ApplicationException

class NoLayerException(ApplicationException): pass

class Action (object):
    """Encodes information about the request -- each property may be parsed out
       of the request and then passed into a datasource for action. the 'method'
       property should be one of select, create, update, delete or metadata."""
    def __init__ (self):
        self.method         = None
        self.layer          = None
        self.feature        = None
        self.id             = None
        self.bbox           = None
        self.maxfeatures    = None
        self.startfeature   = 0
        self.attributes     = {} 
        self.metadata       = None 

class Request (object):

    query_action_types = []

    def __init__ (self, service):
        self.service    = service
        self.datasource = None
        self.actions    = []
        self.host       = None
    
    def encode_metadata(self, action):
        """Accepts an action, which is of method 'metadata' and
           may have one attribute, 'metadata', which includes
           information parsed by the service parse method. This
           should return a content-type, string tuple to be delivered
           as metadata to the Server for delivery to the client."""
        data = []
        if action.metadata:
            data.append(action.metadata)
        else:
            data.append("The following layers are available:")
            for layer in self.service.datasources: 
                data.append(" * %s, %s/%s" % (layer, self.host, layer))
        return ("text/plain", "\n".join(data))
    
    def parse(self, params, path_info, host, post_data, request_method, format_obj = None):
        """Used by most of the subclasses without changes. Does general
           processing of request information using request method and 
           path/parameter information, to build up a list of actions.
           Returns a list of Actions. If the first action in the list is 
           of method 'metadata', encode_metadata is called (no datasource
           is touched), and encode_metadata is called. Otherwise, the actions
           are passed onto DataSources to create lists of Features.""" 
        self.host = host
        
        try:
            self.get_layer(path_info, params)
        except NoLayerException:
            a = Action()
            a.method = "metadata"
            self.actions.append(a)
            return
        
        if not self.service.datasources.has_key(self.datasource):
            raise Exception("Could not find the layer %s: Check your config file? (Available layers are: %s)" % (self.datasource, ",".join(self.service.datasources.keys())))
        
        action = Action()
        
        if request_method == "GET":
           action = self.get_select_action(path_info, params) 
        
        elif request_method == "POST" or request_method == "PUT":
            actions = self.handle_post(params, path_info, host, post_data, request_method, format_obj = format_obj)
            for action in actions:
                self.actions.append(action)
            return    
        
        elif request_method == "DELETE":
            id = self.get_id_from_path_info(path_info)
            if id is not False:
                action.id = id
                action.method = "delete"
        
        self.actions.append(action)
    
    def get_id_from_path_info(self, path_info):
        """Pull Feature ID from path_info and return it."""
        try:
            path = path_info.split("/")
            path_pieces = path[-1].split(".")
            if len(path_pieces) > 1:
                return int(path_pieces[0])
            if path_pieces[0].isdigit():
                return int(path_pieces[0])
        except:
            return False
        return False    
    
    def get_select_action(self, path_info, params):
        """Generate a select action from a URL. Used unmodified by most
           subclasses. Handles attribute query by following the rules passed in
           the DS or in the request, bbox, maxfeatures, and startfeature by
           looking for the parameters in the params. """
        action = Action()
        action.method = "select"

        id = self.get_id_from_path_info(path_info)
        
        if id is not False:
            action.id = id
        
        else:
            queryable = []
            ds = self.service.datasources[self.datasource]
            import sys
            if hasattr(ds, 'queryable'):
                queryable = ds.queryable.split(",") 
            elif params.has_key("queryable"):
                queryable = params['queryable'].split(",")
            for key, value in params.items():
                type = None
                if "__" in key:
                    key, type = key.split("__") 
                if key == 'bbox':
                    action.bbox = map(float, value.split(","))
                elif key == "maxfeatures":
                    action.maxfeatures = int(value)
                elif key == "startfeature":
                    action.startfeature = int(value)
                elif key in queryable or key.upper() in queryable:
                    if type:
                        if type in ds.query_action_types:
                            action.attributes[key] = {'type': type, 'value':value} 
                        else:
                            raise ApplicationException("%s, %s, %s\nYou can't use %s on this layer. Available query action types are: \n%s" % (self, self.query_action_types, type,
                              type, ",".join(ds.query_action_types) or "None"))
                    else:
                        action.attributes[key] = value 
                    
        return action            
    
    def get_layer(self, path_info, params = {}):
        """Return layer based on path, or raise a NoLayerException.""" 
        path = path_info.split("/")
        if len(path) > 1:
            self.datasource = path[1]
        if params.has_key("layer"):
            self.datasource = params['layer']
        
        if not self.datasource:
            raise NoLayerException("Could not obtain data source from layer parameter or path info.")

    def handle_post(self, params, path_info, host, post_data, request_method, format_obj = None):
        """Read data from the request and turn it into an UPDATE/DELETE action.""" 
        if format_obj: 
            actions = []
            
            id = self.get_id_from_path_info(path_info)
            if id is not False:
                action = Action()
                action.method = "update"
                action.id = id 
                
                features = format_obj.decode(post_data)

                action.feature = features[0]
                actions.append(action)
            
            else:
                features = format_obj.decode(post_data)
                
                for feature in features:
                    action = Action()
                    action.method = "create"
                    action.feature = feature
                    actions.append(action)
            return actions
        else:
            raise Exception("Service type does not support adding features.")

    def encode(self, result):
        """Accepts a list of lists of features. Each list is generated by one datasource 
           method call. Must return a (content-type, string) tuple."""
        results = ["Service type doesn't support displaying data, using naive display."""]
        for action in result:
            for i in action:
                data = i.to_dict()
                for key,value in data['properties'].items():
                    if value and isinstance(value, str): 
                        data['properties'][key] = unicode(value,"utf-8")
                results.append(" * %s" % data)
        
        return ("text/plain", "\n".join(results))        
