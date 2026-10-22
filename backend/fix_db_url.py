
from pathlib import Path
from getpass import getpass
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

env_path = Path(".env")
env = dotenv_values(env_path)
raw_url = env.get("DATABASE_URL")

if not raw_url:
    raise SystemExit("DATABASE_URL not found. Check that this is backend/.env.")

url = make_url(raw_url)

print("Host:", url.host)
print("Port:", url.port)
print("Username:", url.username)
print("Database:", url.database)

password = getpass("Enter your actual Supabase database password (hidden): ")
if not password:
    raise SystemExit("Password cannot be empty.")

new_url = url.set(password=password).render_as_string(hide_password=False)

lines = env_path.read_text(encoding="utf-8").splitlines()
updated = False

for i, line in enumerate(lines):
    if line.lstrip().startswith("DATABASE_URL") and "=" in line:
        lines[i] = f"DATABASE_URL={new_url}"
        updated = True
        break

if not updated:
    raise SystemExit(
        "Could not find DATABASE_URL assignment. No file changes were made."
    )

env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Updated DATABASE_URL. Password was not displayed.")
