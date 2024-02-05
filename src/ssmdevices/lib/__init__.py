from typing import Union

def path(*subdirs, platform: Union[bool, str] = False) -> str:
    """return a path to a distribution file inside ssmdevices.lib.

    Args:
        platform:
            if False, assume the file is platform-independent;
            if True, use the current platform;
            otherwise, the name of another architecture with format f'darwin-arm64'
    """
    import os
    from platform import system, machine

    if platform is True:
        bin_name = f'{system().lower()}-{machine().lower()}'
        subdirs = (bin_name,) + tuple(subdirs)
    elif isinstance(platform, str):
        subdirs = (platform,) + tuple(subdirs)

    path = os.path.join(__path__[0], *subdirs)

    if platform is not False:
        children = list(os.listdir(path))
        if len(children) == 1:
            path = os.path.join(path, children[0])
        elif len(children) == 0:
            raise IOError(f'no files in platform directory {path}')
        elif len(children) > 1:
            raise IOError(f'multiple files in platform directory {path}')
        
    return os.path.relpath(path, '.')

