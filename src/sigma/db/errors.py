"""Errors the data layer raises, mapped to HTTP status codes by the API.

Messages are user-facing Spanish: they are shown verbatim in the interface.
"""

from __future__ import annotations


class SigmaError(Exception):
    """Base class for every expected (non-bug) failure."""


class ValidationError(SigmaError):
    """The request is well-formed but not allowed. → HTTP 400"""


class NotFound(SigmaError):
    """The referenced record does not exist. → HTTP 404"""


class DatabaseFileError(SigmaError):
    """The selected database file cannot be used. → HTTP 400"""
