"""
UTXO 관리 모듈
"""
from typing import Dict, Tuple, Optional

from models import TxOutput


class UTXOSet:
    """
    인메모리 UTXO 집합: (txid, index) -> TxOutput 매핑
    """

    def __init__(self):
        self.utxos: Dict[Tuple[str, int], TxOutput] = {}

    def add_output(self, txid: str, index: int, out: TxOutput):
        """UTXO 추가"""
        self.utxos[(txid, index)] = out

    def remove_output(self, txid: str, index: int):
        """UTXO 제거"""
        self.utxos.pop((txid, index), None)

    def get_output(self, txid: str, index: int) -> Optional[TxOutput]:
        """UTXO 조회"""
        return self.utxos.get((txid, index))

    def all_utxos(self) -> Dict[Tuple[str, int], TxOutput]:
        """모든 UTXO 반환"""
        return dict(self.utxos)
