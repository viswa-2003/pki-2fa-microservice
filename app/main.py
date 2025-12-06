from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import time

from cryptography.hazmat.primitives import hashes, serialization  # [web:33]
from cryptography.hazmat.primitives.asymmetric import padding      # [web:33]
from cryptography.hazmat.backends import default_backend           # [web:38]

import base64
import pyotp                                                       # [web:28]

app = FastAPI()

# ---------- Key loading ----------

with open("student_private.pem", "rb") as f:                       # [web:38]
    PRIVATE_KEY = serialization.load_pem_private_key(
        f.read(),
        password=None,
        backend=default_backend(),
    )

# ---------- Crypto helpers ----------

def decrypt_seed(encrypted_seed_b64: str, private_key=PRIVATE_KEY) -> str:
    """
    Decrypt base64-encoded encrypted seed using RSA/OAEP(SHA-256).
    Returns 64-char lowercase hex string or raises ValueError. [web:33][web:39]
    """
    try:
        ciphertext = base64.b64decode(encrypted_seed_b64.strip())

        plaintext_bytes = private_key.decrypt(                     # [web:33][web:39]
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        seed_hex = plaintext_bytes.decode("utf-8").strip()

        if len(seed_hex) != 64:
            raise ValueError("Decrypted seed must be 64 characters")
        allowed = set("0123456789abcdef")
        if any(ch not in allowed for ch in seed_hex):
            raise ValueError("Decrypted seed must be lowercase hex")

        return seed_hex
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")

def save_seed_to_file(seed_hex: str, path: str = "/data/seed.txt"):
    Path("/data").mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(seed_hex + "\n")

def load_seed_from_file(path: str = "/data/seed.txt") -> str:
    seed_path = Path(path)
    if not seed_path.exists():
        raise FileNotFoundError("Seed not decrypted yet")
    with open(seed_path) as f:
        return f.read().strip()

def generate_totp_code(hex_seed: str) -> str:
    # 1. Convert hex seed (64-char) to bytes
    seed_bytes = bytes.fromhex(hex_seed)

    # 2. Convert bytes to Base32 string
    base32_seed = base64.b32encode(seed_bytes).decode("utf-8")  # [web:42]

    # 3. Create TOTP with defaults: SHA-1, 30s interval, 6 digits [web:28][web:47]
    totp = pyotp.TOTP(base32_seed)

    # 4. Generate current code
    return totp.now()

def verify_totp_code(hex_seed: str, code: str, valid_window: int = 1) -> bool:
    # 1. Same hex→bytes→base32 as in generate_totp_code
    seed_bytes = bytes.fromhex(hex_seed)
    base32_seed = base64.b32encode(seed_bytes).decode("utf-8")

    # 2. Same TOTP parameters
    totp = pyotp.TOTP(base32_seed)

    # 3. Verify with time window tolerance ±1 period (±30s) [web:28][web:46]
    return totp.verify(code, valid_window=valid_window)
    # [web:28][web:59]

def seconds_remaining_in_period(period: int = 30) -> int:
    now = int(time.time())
    return period - (now % period)

# ---------- Request models ----------

class DecryptSeedRequest(BaseModel):
    encrypted_seed: str

class Verify2FARequest(BaseModel):
    code: str | None = None

# ---------- Endpoint 1: POST /decrypt-seed ----------

@app.post("/decrypt-seed")
async def decrypt_seed_endpoint(body: DecryptSeedRequest):
    try:
        seed_hex = decrypt_seed(body.encrypted_seed)
        save_seed_to_file(seed_hex)
        return {"status": "ok"}
    except ValueError:
        # Any decryption validation error must return 500 with standard message
        raise HTTPException(status_code=500, detail="Decryption failed")

# ---------- Endpoint 2: GET /generate-2fa ----------

@app.get("/generate-2fa")
async def generate_2fa():
    try:
        seed_hex = load_seed_from_file()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Seed not decrypted yet")

    code = generate_totp_code(seed_hex)
    valid_for = seconds_remaining_in_period(30)                    # [web:47]

    return {"code": code, "valid_for": valid_for}

# ---------- Endpoint 3: POST /verify-2fa ----------

@app.post("/verify-2fa")
async def verify_2fa(body: Verify2FARequest):
    if not body.code:
        raise HTTPException(status_code=400, detail="Missing code")

    try:
        seed_hex = load_seed_from_file()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Seed not decrypted yet")

    is_valid = verify_totp_code(seed_hex, body.code, valid_window=1)

    return {"valid": is_valid}
