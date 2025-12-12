"""
암호화 및 해시 유틸리티 모듈
"""
import hashlib

try:
    from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError
except ImportError:
    SigningKey = None
    VerifyingKey = None
    BadSignatureError = Exception
    SECP256k1 = None


def sha256_bytes(data: bytes) -> bytes:
    """바이트 데이터를 SHA-256 해시하여 바이트로 반환"""
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    """바이트 데이터를 SHA-256 해시하여 16진수 문자열로 반환"""
    return hashlib.sha256(data).hexdigest()
