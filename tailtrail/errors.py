"""Stable package error hierarchy with non-sensitive diagnostics."""


class TailTrailError(Exception):
    """Base class for supported TailTrail package errors."""


class UnsupportedPythonError(TailTrailError):
    """Raised when the interpreter is outside the declared support window."""


class PackageResourceError(TailTrailError):
    """Raised when required installed package content is missing or corrupt."""
