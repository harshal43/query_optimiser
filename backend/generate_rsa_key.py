"""Run once to generate RSA key pair for Snowflake key-pair auth."""
from __future__ import annotations
import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, PublicFormat,
)

OUT_DIR = Path(__file__).parent / "keys"
OUT_DIR.mkdir(exist_ok=True)

PRIVATE_KEY_PATH = OUT_DIR / "rsa_key.p8"
PUBLIC_KEY_PATH  = OUT_DIR / "rsa_key.pub"

if PRIVATE_KEY_PATH.exists():
    print(f"Key already exists at {PRIVATE_KEY_PATH} — delete it first to regenerate.")
else:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    PRIVATE_KEY_PATH.write_bytes(
        key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    PUBLIC_KEY_PATH.write_bytes(
        key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    print(f"Private key : {PRIVATE_KEY_PATH.resolve()}")
    print(f"Public key  : {PUBLIC_KEY_PATH.resolve()}")

# Show the public key value to paste into Snowflake (strip header/footer)
pub_pem = PUBLIC_KEY_PATH.read_text()
pub_lines = [l for l in pub_pem.splitlines() if not l.startswith("-----")]
pub_b64 = "".join(pub_lines)

print("\n--- Paste this into Snowflake (no header/footer lines) ---")
print(pub_b64)
print("----------------------------------------------------------")
print("\nSnowflake SQL to run:")
print(f"ALTER USER <your_user> SET RSA_PUBLIC_KEY='{pub_b64}';")
print(f"\nAdd to .env:")
print(f"SNOWFLAKE_PRIVATE_KEY_PATH={PRIVATE_KEY_PATH.resolve()}")
