from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials
import os
import base64
import json

# Initialize Firebase Admin
cred_path = os.environ.get('FIREBASE_CREDENTIALS')
if cred_path and os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin initialized.")
else:
    print("WARNING: FIREBASE_CREDENTIALS not set or file not found. Decoding JWT claims without verification (dev mode).")
    try:
        firebase_admin.initialize_app()
    except ValueError:
        pass  # Already initialized

security = HTTPBearer()


def _decode_jwt_claims(token: str) -> dict:
    """
    Decode a Firebase JWT without signature verification.
    Used in dev mode (no Firebase Admin credentials).
    Extracts real user_id/sub so the UID is stable across sessions.
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload = parts[1]
        # Add base64 padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    if not cred_path:
        # Dev mode — no Firebase Admin SDK credentials available.
        # Decode the JWT to extract the real UID (user_id / sub).
        # This is NOT secure (no signature verification) but gives a stable
        # UID that matches across sessions, so the DB lookup works correctly.
        if token == "mock-token":
            return {"uid": "mock-user-id"}

        claims = _decode_jwt_claims(token)
        uid = claims.get("user_id") or claims.get("sub")
        if uid:
            print(f"[DEV] Decoded UID from JWT: {uid}")
            return {"uid": uid}

        # Fallback: shouldn't reach here with a real Firebase JWT
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not decode token UID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(decoded_token: dict = Depends(verify_token)) -> str:
    return decoded_token.get("uid")
