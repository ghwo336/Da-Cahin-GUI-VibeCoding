"""
지갑 관리 모듈
"""
from crypto import sha256_hex, SigningKey, VerifyingKey, SECP256k1, BadSignatureError


class Wallet:
    """
    ECDSA 개인/공개 키 쌍을 관리하는 지갑
    """

    def __init__(self):
        if SigningKey is None:
            raise RuntimeError("ecdsa library is required. Install with 'python3 -m pip install ecdsa'.")
        self.sk: SigningKey = SigningKey.generate(curve=SECP256k1)
        self.vk: VerifyingKey = self.sk.get_verifying_key()

    @property
    def pubkey_bytes(self) -> bytes:
        """공개키 바이트"""
        return self.vk.to_string()

    @property
    def pubkey_hex(self) -> str:
        """공개키 16진수 문자열"""
        return self.pubkey_bytes.hex()

    @property
    def pubkey_hash(self) -> str:
        """공개키 해시"""
        return sha256_hex(self.pubkey_bytes)

    def sign(self, msg_hash_hex: str) -> str:
        """메시지 해시에 서명"""
        msg_bytes = bytes.fromhex(msg_hash_hex)
        sig = self.sk.sign(msg_bytes)
        return sig.hex()

    @staticmethod
    def verify(pubkey_hex: str, msg_hash_hex: str, signature_hex: str) -> bool:
        """서명 검증"""
        if VerifyingKey is None:
            raise RuntimeError("ecdsa library is required. Install with 'python3 -m pip install ecdsa'.")
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(pubkey_hex), curve=SECP256k1)
            vk.verify(bytes.fromhex(signature_hex), bytes.fromhex(msg_hash_hex))
            return True
        except BadSignatureError:
            return False
        except Exception:
            return False
