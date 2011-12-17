from vectorformats.Formats.Format import Format
import re, xml.dom.minidom as m

class WFS(Format):
    """WFS-like GML writer."""

    layername = "layer"
    def encode(self, features, **kwargs):
        results = ["""<wfs:FeatureCollection
   xmlns:fs="http://example.com/featureserver"
   xmlns:wfs="http://www.opengis.net/wfs"
   xmlns:gml="http://www.opengis.net/gml"
   xmlns:ogc="http://www.opengis.net/ogc"
   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengeospatial.net//wfs/1.0.0/WFS-basic.xsd">
        """]
        for feature in features:
            results.append( self.encode_feature(feature))
        results.append("""</wfs:FeatureCollection>""")
        return "\n".join(results)        
    
    def encode_feature(self, feature):
        layername = re.sub(r'\W', '_', self.layername)
        
        attr_fields = [] 
        for key, value in feature.properties.items():
            key = re.sub(r'\W', '_', key)
            attr_value = value
            if hasattr(attr_value,"replace"): 
                attr_value = attr_value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if isinstance(attr_value, str):
                attr_value = unicode(attr_value, "utf-8")
            attr_fields.append( "<fs:%s>%s</fs:%s>" % (key, attr_value,key) )
            
        
        
        xml = """
        <gml:featureMember><fs:%s fid="%s">
        <fs:geometry>
        %s
        </fs:geometry>
        %s
        </fs:%s></gml:featureMember>""" % (layername, feature.id, self.geometry_to_gml(feature.geometry), "\n".join(attr_fields), layername)  
        return xml
    
    def geometry_to_gml(self, geometry):
        """
        >>> w = WFS()
        >>> print w.geometry_to_gml({'type':'Point', 'coordinates':[1.0,2.0]})
        <gml:Point><gml:coordinates>1.0,2.0</gml:coordinates></gml:Point>
        >>> w.geometry_to_gml({'type':'LineString', 'coordinates':[[1.0,2.0],[2.0,1.0]]})
        '<gml:LineString><gml:coordinates>1.0,2.0 2.0,1.0</gml:coordinates></gml:LineString>'
        """
        
        if geometry['type'] == "Point":
            coords = ",".join(map(str, geometry['coordinates']))
            return "<gml:Point><gml:coordinates>%s</gml:coordinates></gml:Point>" % coords
        elif geometry['type'] == "LineString":
            coords = " ".join(",".join(map(str, coord)) for coord in geometry['coordinates'])
            return "<gml:LineString><gml:coordinates>%s</gml:coordinates></gml:LineString>" % coords
        elif geometry['type'] == "Polygon":
            coords = " ".join(map(lambda x: ",".join(map(str, x)), geometry['coordinates'][0]))
            out = """
              <gml:outerBoundaryIs><gml:LinearRing>
              <gml:coordinates>%s</gml:coordinates>
              </gml:LinearRing></gml:outerBoundaryIs>
            """ % coords 
            inner_rings = []
            for inner_ring in geometry['coordinates'][1:]:
                coords = " ".join(map(lambda x: ",".join(map(str, x)), inner_ring))
                inner_rings.append("""
                  <gml:innerBoundaryIs><gml:LinearRing>
                  <gml:coordinates>%s</gml:coordinates>
                  </gml:LinearRing></gml:innerBoundaryIs>
                """ % coords) 
            return """<gml:Polygon>
              %s %s
              </gml:Polygon>""" % (out, "\n".join(inner_rings))
        else:
            raise Exception("Could not convert geometry of type %s." % geometry['type'])  
