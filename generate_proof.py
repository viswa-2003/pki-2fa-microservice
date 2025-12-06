import base64
import subprocess

from cryptography.hazmat.primitives import hashes, serialization  # [web:107][web:111]
from cryptography.hazmat.primitives.asymmetric import padding     # [web:107][web:111]
from cryptography.hazmat.backends import default_backend          # [web:38]

def load_student_private_key(path: str = "student_private.pem"):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend(),
        )                                                          # [web:38]

def load_instructor_public_key(path: str = "instructor_public.pem"):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(
            f.read(),
            backend=default_backend(),
        )                                                          # [web:38]

def sign_message(message: str, private_key) -> bytes:
    """
    Sign commit hash using RSA-PSS with SHA-256.
    """
    message_bytes = message.encode("utf-8")  # ASCII/UTF-8 string

    signature = private_key.sign(                               # [web:107][web:111]
        message_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return signature

def encrypt_with_public_key(data: bytes, public_key) -> bytes:
    """
    Encrypt data using RSA/OAEP with SHA-256.
    """
    ciphertext = public_key.encrypt(                            # [web:107][web:112]
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return ciphertext

def get_latest_commit_hash() -> str:
    """
    Run `git log -1 --format=%H` and return the 40-char commit hash.
    """
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H"],
        capture_output=True,
        text=True,
        check=True,
    )
    commit_hash = result.stdout.strip()
    if len(commit_hash) != 40:
        raise ValueError(f"Unexpected commit hash length: {commit_hash}")
    return commit_hash

def main():
    # 1. Get commit hash
    commit_hash = get_latest_commit_hash()

    # 2. Load keys
    student_priv = load_student_private_key()
    instructor_pub = load_instructor_public_key()

    # 3. Sign commit hash with student private key (RSA-PSS-SHA256)
    signature = sign_message(commit_hash, student_priv)

    # 4. Encrypt signature with instructor public key (RSA/OAEP-SHA256)
    encrypted_sig = encrypt_with_public_key(signature, instructor_pub)

    # 5. Base64 encode encrypted signature (single line string)
    encrypted_sig_b64 = base64.b64encode(encrypted_sig).decode("utf-8")

    # 6. Print values for submission
    print("Commit Hash:")
    print(commit_hash)
    print("\nEncrypted Signature:")
    print(encrypted_sig_b64)

if __name__ == "__main__":
    main()
