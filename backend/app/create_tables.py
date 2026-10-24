
from app.database import Base, engine
from app import models  # Registers all four models with Base.metadata


def main():
    Base.metadata.create_all(bind=engine)
    print("Table creation command completed.")

    print("Tables found:")
    for table_name in sorted(Base.metadata.tables):
        print(f"- {table_name}")


if __name__ == "__main__":
    main()
