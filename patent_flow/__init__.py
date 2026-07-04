from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("patent-flow-skill")
except PackageNotFoundError:
    __version__ = "dev"
