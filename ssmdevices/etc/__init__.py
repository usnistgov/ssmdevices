# Including this file ensures this directory is installed by setuptools


def default_path(cls):
    """Return a module imported from the provided path to a dll
    that contains a .NET library called `libname.`

    :param cls: the class

    :param module_: the module where the config lives
    """

    global __path__
    import os

    mod_split = cls.__module__.split('.', 1)[-1]
    rel_path = (mod_split + '.' + cls.__name__).replace('.', os.path.sep)
    return os.path.join(__path__[0], rel_path)
