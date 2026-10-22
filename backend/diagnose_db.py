
import os
import psycopg
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv(override=True)

try:
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        print("RESULT: DATABASE_URL missing")
        raise SystemExit(1)

    url = make_url(raw_url)

    with psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=url.password,
        connect_timeout=10,
        sslmode="require",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            print("RESULT: CONNECTED")
            print("Query result:", cur.fetchone()[0])

except SystemExit:
    raise
except Exception as exc:
    message = str(exc).lower()
    print("RESULT: FAILED")
    print("Error type:", type(exc).__name__)

    if "password authentication failed" in message:
        print("CAUSE: Authentication rejected")
    elif "tenant or user not found" in message:
        print("CAUSE: Pooler username or project reference rejected")
    elif "timeout" in message or "timed out" in message:
        print("CAUSE: Connection timeout")
    elif "ssl" in message or "tls" in message or "certificate" in message:
        print("CAUSE: SSL/TLS")
    elif "connection refused" in message:
        print("CAUSE: Connection refused")
    elif "could not translate host" in message:
        print("CAUSE: Hostname resolution")
    else:
        print("CAUSE: Other connection failure; details hidden")
