"""Stable public Python API for TailTrail.

Only the names exported here are covered by the Python API compatibility
promise. Repository scripts and ``tailtrail.scripts`` remain CLI implementation
details.
"""

from .api import ExitCode, PackageStatus, package_status


def main(argv=None):
    """Run the supported TailTrail CLI without importing it during package import."""
    from .cli import main as cli_main

    return cli_main(argv)

__all__ = ["ExitCode", "PackageStatus", "main", "package_status"]
__version__ = "0.6.0"
