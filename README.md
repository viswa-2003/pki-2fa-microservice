# PKI 2FA Microservice

A small PKI-backed 2FA microservice built with FastAPI, RSA cryptography, TOTP, Docker, and cron. The service decrypts a per-student seed using RSA, generates TOTP 2FA codes, verifies codes, and logs them periodically via a cron job inside the container. [web:146][web:153]

## Features

- RSA 4096-bit key pair for a student identity (PEM format).
- RSA/OAEP (SHA-256, MGF1-SHA256) decryption of an encrypted seed. [web:107][web:111]
- RSA-PSS (SHA-256, MGF1-SHA256) signing of the final Git commit hash for proof-of-work. [web:110][web:113]
- TOTP (RFC 6238) 2FA codes from a 64-character hex seed:
  - SHA-1, 30-second step, 6 digits. [web:47]
  - Implemented with `pyotp`.
- REST API implemented with FastAPI:
  - `POST /decrypt-seed`
  - `GET /generate-2fa`
  - `POST /verify-2fa` [web:51]
- Dockerized with Docker Compose:
  - Multi-stage build.
  - Named volumes for seed and cron output.
  - Cron daemon running inside the container. [web:146][web:152]
- Cron job logs TOTP codes every minute with UTC timestamps to `/cron/last_code.txt`.

## Tech Stack

- **Language:** Python 3
- **Framework:** FastAPI + Uvicorn
- **Crypto:** `cryptography`, `pyotp` [web:107][web:28]
- **Containerization:** Docker, Docker Compose [web:80][web:153]
- **Scheduling:** Linux `cron`

## Project Structure

- `app/main.py`  
  FastAPI application, RSA decryption, TOTP generation/verification, file persistence under `/data`. [web:51]

- `generate_keys.py`  
  Generates `student_private.pem` and `student_public.pem` (RSA 4096-bit, exponent 65537).

- `request_seed.py`  
  Calls the instructor API with:
  - `student_id`
  - `github_repo_url`
  - `student_public.pem` (PEM as JSON string)  
  and saves `encrypted_seed.txt` (base64). [web:70]

- `generate_proof.py`  
  - Reads latest Git commit hash.  
  - Signs it with RSA-PSS-SHA256 using `student_private.pem`.  
  - Encrypts the signature with `instructor_public.pem` via RSA/OAEP-SHA256.  
  - Outputs:
    - Commit hash
    - Base64 encrypted signature (for submission). [web:107][web:113]

- `cron/2fa-cron`  
  Crontab entry (LF endings enforced via `.gitattributes`):  
  Runs `log_2fa_cron.py` every minute. [web:152]

- `scripts/log_2fa_cron.py`  
  - Reads `/data/seed.txt`.  
  - Computes current TOTP code.  
  - Logs `YYYY-MM-DD HH:MM:SS - 2FA Code: XXXXXX` to `/cron/last_code.txt` (UTC). [web:152]

- `Dockerfile`  
  - Multi-stage build on `python:3.11-slim`.  
  - Installs `cron`, `tzdata`, sets `TZ=UTC`.  
  - Copies app, scripts, cron config, and key files.  
  - Registers cron job and starts `cron` + Uvicorn on `0.0.0.0:8080`. [web:146][web:152]

- `docker-compose.yml`  
  - Builds the image from the `Dockerfile`.  
  - Exposes `8080:8080`.  
  - Mounts named volumes:
    - `seed-data` → `/data`
    - `cron-output` → `/cron`  
  - Binds local key files into `/app/*.pem`. [web:78]

- `.gitignore`  
  - Ignores `encrypted_seed.txt`, caches, env files, IDE files.

- `.gitattributes`  
  - Ensures `cron/2fa-cron` uses `LF` line endings.

- `student_private.pem`, `student_public.pem`, `instructor_public.pem`  
  - RSA keys required for decryption and commit proof (assignment-specific; **not for production use**).

## Setup and Usage

### 1. Install dependencies (local dev)
pip install -r requirements.txt

Dependencies include:

- `fastapi`
- `uvicorn`
- `cryptography`
- `pyotp`
- `requests` [web:119][web:28]

### 2. Generate student keys

python generate_keys.py

This creates:

- `student_private.pem`
- `student_public.pem`

### 3. Download instructor public key

Download `instructor_public.pem` from the course resource URL and place it in the project root.

### 4. Request encrypted seed

Update `request_seed.py` with:

- `STUDENT_ID`
- `GITHUB_REPO_URL` (exact URL for this repo)

Then:

python request_seed.py

This creates `encrypted_seed.txt` (base64) — **do not commit this file**.

### 5. Build and run with Docker

docker compose build
docker compose up -d

Check the container:
docker ps

### 6. Call API endpoints

1. **Decrypt seed**
curl -X POST http://localhost:8080/decrypt-seed
-H "Content-Type: application/json"
-d "{"encrypted_seed": "$(cat encrypted_seed.txt)"}"

Response: `{"status":"ok"}` and `/data/seed.txt` is created in the container.

2. **Generate 2FA code**
curl http://localhost:8080/generate-2fa

Example response:
{"code":"123456","valid_for":23}

3. **Verify valid code**
CODE=123456 # paste from previous response quickly
curl -X POST http://localhost:8080/verify-2fa
-H "Content-Type: application/json"
-d "{"code": "$CODE"}"

Response: `{"valid":true}`

4. **Verify invalid code**
curl -X POST http://localhost:8080/verify-2fa
-H "Content-Type: application/json"
-d '{"code": "000000"}'

Response: `{"valid":false}`

### 7. Check cron output

Wait at least 70 seconds after seed decryption, then:

docker exec pki-2fa-service sh -c 'cat /cron/last_code.txt'

You should see lines like:

2025-12-06 19:10:01 - 2FA Code: 715042

indicating cron runs every minute and logs UTC timestamps. [web:152]

### 8. Restart persistence test

docker compose restart
sleep 10
curl http://localhost:8080/generate-2fa

`/generate-2fa` should still work without calling `/decrypt-seed` again, showing seed persistence via the `/data` volume. [web:78]

## Commit Proof (Assignment-Specific)

To generate the commit proof:

1. Ensure all changes are committed:

git status

2. Run:

python generate_proof.py

This prints:

- **Commit Hash** – latest `git log -1 --format=%H`
- **Encrypted Signature** – base64 string: RSA-PSS signature of the hash, encrypted via RSA/OAEP using the instructor’s public key. [web:107][web:113]

These are submitted along with:

- GitHub repo URL
- `student_public.pem` contents
- `encrypted_seed.txt` contents

## Production Notes (Non-Assignment)

This implementation is intentionally simplified for the assignment. For production, you would:

- Move private keys into a secure secret store (not committed or baked into the image). [web:141][web:144]
- Require authentication/authorization for all endpoints and expose them only over HTTPS via a gateway. [web:139][web:140]
- Harden Docker images (non-root user, reduced attack surface), add security scanning, and central logging/monitoring. [web:134][web:144]
- Avoid logging real TOTP codes in plaintext outside controlled environments. [web:142][web:145]













In a virtual environment:

