class Format(object):
    """Base Format class. To set properties on your subclasses, you can
       pass them as kwargs to your format constructor."""
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
            
