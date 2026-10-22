
import os
import socket
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

load_dotenv(override=True)

raw_url = os.getenv("DATABASE_URL")

if not raw_url:
    print("FAILED: DATABASE_URL is missing.")
    raise SystemExit(1)

try:
    url = make_url(raw_url)

    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")

    if not url.host:
        print("FAILED: No database hostname found.")
        raise SystemExit(1)

    print("Hostname:", url.host)
    print("Port:", url.port or 5432)

    try:
        addresses = socket.getaddrinfo(
            url.host, url.port or 5432,
            type=socket.SOCK_STREAM
        )
        print("Python DNS: SUCCESS")
        print("Resolved addresses:", len(addresses))
    except socket.gaierror:
        print("Python DNS: FAILED")
        print("Windows nslookup may be resolving this differently.")
        raise SystemExit(1)

    engine = create_engine(
        url,
        connect_args={
            "connect_timeout": 10,
            "sslmode": "require",
            },
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("DATABASE CONNECTION: SUCCESS")
            print("Test query result:", result.scalar())

    except SQLAlchemyError as exc:
        original = getattr(exc, "orig", None)
        sqlstate = getattr(original, "sqlstate", None)

        print("DATABASE CONNECTION: FAILED")
        print("Error type:", type(exc).__name__)

        if sqlstate:
            print("SQLSTATE:", sqlstate)
        else:
            print("SQLSTATE: unavailable")

        print("Full error hidden to protect connection details.")

    finally:
        engine.dispose()

except SystemExit:
    raise

except SQLAlchemyError as exc:
    original = getattr(exc, "orig", None)
    message = str(original or exc).lower()
    sqlstate = getattr(original, "sqlstate", None)

    print("DATABASE CONNECTION: FAILED")

    if sqlstate:
        print("SQLSTATE:", sqlstate)

    if "password authentication failed" in message:
        print("CAUSE: Database username/password rejected.")
    elif "role" in message and "does not exist" in message:
        print("CAUSE: Database username/role is incorrect.")
    elif "database" in message and "does not exist" in message:
        print("CAUSE: Database name is incorrect.")
    elif "certificate" in message or "ssl" in message or "tls" in message:
        print("CAUSE: SSL/TLS negotiation or certificate issue.")
    elif "timeout" in message or "timed out" in message:
        print("CAUSE: Database connection timed out.")
    elif "too many connections" in message:
        print("CAUSE: Database connection limit reached.")
    elif "could not translate host name" in message:
        print("CAUSE: Hostname resolution failed during connection.")
    elif "connection refused" in message:
        print("CAUSE: Database endpoint refused the connection.")
    elif "no pg_hba.conf entry" in message:
        print("CAUSE: Database connection policy rejected the connection.")
    else:
        print("CAUSE: Unclassified database connection error.")
        print("DETAILS: Hidden for credential safety.")
