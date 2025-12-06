#!/usr/bin/env python3

from datetime import datetime, timezone
from pathlib import Path
import sys
import os

# Ensure we can import from app.main
sys.path.insert(0, "/app")

try:
    from app.main import generate_totp_code, load_seed_from_file
except Exception as e:
    print(f"ERROR: Failed to import app functions: {e}", file=sys.stderr)
    sys.exit(1)

def main():
    try:
        # 1. Read hex seed from /data/seed.txt
        try:
            seed_hex = load_seed_from_file("/data/seed.txt")
        except FileNotFoundError:
            print("ERROR: Seed file /data/seed.txt not found", file=sys.stderr)
            return

        # 2. Generate current TOTP code
        code = generate_totp_code(seed_hex)

        # 3. Get current UTC timestamp
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S")

        # 4. Output formatted line to stdout (cron redirects to /cron/last_code.txt)
        print(f"{timestamp} - 2FA Code: {code}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
