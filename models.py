"""
블록체인 데이터 구조 모델
"""
import json
from dataclasses import dataclass, field
from typing import List

from crypto import sha256_hex


@dataclass
class TxOutput:
    """트랜잭션 출력"""
    asset_id: str
    pubkey_hash: str  # hex string
    portion: int      # percentage (0~100)

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "pubkey_hash": self.pubkey_hash,
            "portion": self.portion,
        }


@dataclass
class TxInput:
    """트랜잭션 입력"""
    txid_ref: str     # referenced transaction id
    index: int        # output index
    pubkey: str       # hex encoded public key
    signature: str    # hex encoded signature

    def to_dict(self, include_signature: bool = True) -> dict:
        d = {
            "txid_ref": self.txid_ref,
            "index": self.index,
            "pubkey": self.pubkey,
        }
        if include_signature:
            d["signature"] = self.signature
        return d


@dataclass
class Transaction:
    """트랜잭션"""
    inputs: List[TxInput]
    outputs: List[TxOutput]
    txid: str = field(init=False)

    def __post_init__(self):
        self.txid = self.compute_txid()

    def _serialize(self, include_signatures: bool = True) -> bytes:
        """트랜잭션 직렬화"""
        data = {
            "inputs": [inp.to_dict(include_signature=include_signatures) for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
        }
        s = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return s.encode("utf-8")

    def compute_txid(self) -> str:
        """트랜잭션 ID 계산 (서명 포함)"""
        return sha256_hex(self._serialize(include_signatures=True))

    def message_hash(self) -> str:
        """서명용 메시지 해시 (서명 제외)"""
        return sha256_hex(self._serialize(include_signatures=False))


@dataclass
class BlockHeader:
    """블록 헤더"""
    height: int
    prev_hash: str
    merkle_root: str
    nonce: int

    def to_dict(self) -> dict:
        return {
            "height": self.height,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
        }

    def hash(self) -> str:
        """블록 헤더 해시 계산"""
        s = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256_hex(s)


@dataclass
class Block:
    """블록"""
    header: BlockHeader
    txs: List[Transaction]
