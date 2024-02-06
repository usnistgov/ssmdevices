from typing import Union


def path(*subdirs, platform: Union[bool, str] = False) -> str:
    """return a path to a distribution file inside ssmdevices.lib.

    Args:
        platform:
            if False, assume the file is platform-independent;
            if True, use the current platform;
            otherwise, the name of another architecture with format f'darwin-arm64'
    """

    from pathlib import Path
    from platform import system, machine

    if platform is True:
        platform_name = f'{system().lower()}-{machine().lower()}'
        subdirs = (platform_name,) + tuple(subdirs)
    elif isinstance(platform, str):
        subdirs = (platform,) + tuple(subdirs)

    path = Path(__path__[0], *subdirs)

    if platform is not False:
        children = [p for p in path.iterdir() if p.stem.lower() == subdirs[-1].lower()]
        if len(children) == 1:
            path = path/children[0]
        elif len(children) == 0:
            raise IOError(f'no files matched {platform_name} in platform directory {path}')
        elif len(children) > 1:
            raise IOError(f'multiple files matched {platform_name} in platform directory {path}')

    return str(path.relative_to(Path('.').absolute()))