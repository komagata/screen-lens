"""Check all installed requirements, allowing only the documented OpenCV substitute."""
from importlib import metadata
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def check():
    try:
        metadata.version('opencv-python')
    except metadata.PackageNotFoundError:
        pass
    else:
        raise RuntimeError('Full OpenCV must not coexist with headless OpenCV')
    for distribution in metadata.distributions():
        for text in distribution.requires or []:
            requirement = Requirement(text)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            name = canonicalize_name(requirement.name)
            if name == 'opencv-python' and canonicalize_name(distribution.name) == 'rapidocr':
                name = 'opencv-python-headless'
            version = metadata.version(name)
            if requirement.specifier and version not in requirement.specifier:
                raise RuntimeError('Unsatisfied runtime dependency: ' + name)
    import cv2
    if 'NONE' not in next(line for line in cv2.getBuildInformation().splitlines() if line.strip().startswith('GUI:')):
        raise RuntimeError('OpenCV GUI dependencies are still enabled')


if __name__ == '__main__':
    check()
    print('Slim runtime requirements and headless OpenCV verified')
