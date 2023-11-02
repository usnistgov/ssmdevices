def path(*subdirs):
    import os

    return os.path.join(__path__[0], *subdirs)
