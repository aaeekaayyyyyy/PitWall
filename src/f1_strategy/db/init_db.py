"""Entrypoint to create all database tables. Run with: python -m f1_strategy.db.init_db"""

from f1_strategy.db import create_tables


def main() -> None:
    create_tables()
    print("Tables created successfully.")


if __name__ == "__main__":
    main()
