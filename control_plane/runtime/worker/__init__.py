"""Worker process package.

The package initializer intentionally avoids importing infrastructure adapters so
pure domain/mapping modules remain usable without Redis or database drivers.
"""
