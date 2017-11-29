import configparser


class ConfigAdapter:
    """
    Behaves as Singleton when called with the same filename.
    """

    def __new__(cls, filename):
        if not hasattr(cls, '_instances'):
            setattr(cls, '_instances', {})

        if filename not in getattr(cls, '_instances'):
            # Call super to eliminate infinite recursion
            # You must not pass args and kwargs, because base class 'object'
            # takes only one argument, class object which instance must be
            # created. According to __new__ method specification, it must return
            # empty instance of the class. Actual instance initialization
            # call takes place in metaclass __call__ method.
            _instance = super().__new__(cls)
            getattr(cls, '_instances')[filename] = _instance

        return getattr(cls, '_instances')[filename]

    def __init__(self, filename):
        self.config = configparser.ConfigParser()
        self.config.read(filename)

    def __getattr__(self, item):
        return getattr(self.config, item)

    def __getitem__(self, item):
        return self.config[item]

    def __contains__(self, item):
        return item in self.config
