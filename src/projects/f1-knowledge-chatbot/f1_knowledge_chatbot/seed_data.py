"""Refresh active source-backed tables; legacy partial snapshots are not queried."""
from database import F1Database
if __name__ == "__main__":
    database=F1Database()
    print("Historical data and versioned documents loaded.")
