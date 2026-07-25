"""Data layer: SQLite access split by topic.

Every module here takes an explicit ``db_path`` and opens a short-lived
connection through :func:`sigma.db.connection.connect`. There is no global
connection and no ORM: the database file is user-selectable and may live in a
synced folder, so connections are opened and closed around each operation.
"""

from sigma.db.connection import connect, transaction

__all__ = ["connect", "transaction"]
