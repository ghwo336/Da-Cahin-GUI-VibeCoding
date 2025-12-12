"""
풀 노드 네트워크 모듈
"""
from typing import List, Dict, Optional, TYPE_CHECKING

from blockchain import Blockchain, TARGET_HEX
from models import Transaction, Block

if TYPE_CHECKING:
    from processes import MasterProcess


class FullNode:
    """
    풀 노드 구현 (단순화된 P2P 네트워크 시뮬레이션)
    - 트랜잭션 수신 및 검증
    - 멤풀 관리
    - 블록 채굴
    - 블록 수신 및 검증
    """

    def __init__(self, node_id: str, blockchain: Blockchain, master: Optional["MasterProcess"] = None):
        self.node_id = node_id
        self.blockchain = blockchain
        self.mempool: Dict[str, Transaction] = {}
        self.peers: List["FullNode"] = []
        self.last_mined_block: Optional[Block] = None
        self.master = master

    def connect_peer(self, peer: "FullNode"):
        """피어 연결"""
        if peer not in self.peers:
            self.peers.append(peer)

    def receive_transaction(self, tx: Transaction):
        """
        트랜잭션 수신 및 검증
        - 검증 통과 시 멤풀에 추가하고 피어에게 전파
        """
        if tx.txid in self.mempool:
            return

        ok, reason = self.blockchain.validate_transaction(tx)
        if not ok:
            print(f"[{self.node_id}] reject tx {tx.txid}: {reason}")
            return

        self.mempool[tx.txid] = tx
        # 피어에게 전파
        for p in self.peers:
            p.receive_transaction(tx)

    def mine(self):
        """
        블록 채굴
        - 멤풀에서 유효한 트랜잭션 선택
        - PoW 수행
        - 채굴 성공 시 피어에게 전파
        """
        if not self.mempool:
            print(f"[{self.node_id}] nothing to mine")
            return None

        txs = list(self.mempool.values())
        try:
            block = self.blockchain.mine_block(txs)
        except RuntimeError as e:
            print(f"[{self.node_id}] mining failed: {e}")
            return None

        self.last_mined_block = block

        # 포함된 트랜잭션 멤풀에서 제거
        for tx in block.txs:
            self.mempool.pop(tx.txid, None)

        # 피어에게 블록 전파
        for p in self.peers:
            p.receive_block(block)

        print(f"[{self.node_id}] mined block height={block.header.height}")

        # 마스터 프로세스에 보고
        if self.master is not None:
            self.master.on_block_mined(self, block)

        return block

    def receive_block(self, block: Block):
        """
        블록 수신 및 검증
        - PoW 검증
        - 트랜잭션 검증
        - 블록체인에 추가
        """
        header = block.header
        prev_hash = header.prev_hash
        tip_hash = self.blockchain.height_tip_hash

        # 현재 tip에만 연결 (포크 무시)
        if tip_hash and prev_hash != tip_hash:
            return

        # PoW 검증
        target_int = int(TARGET_HEX, 16)
        h = header.hash()
        if int(h, 16) >= target_int:
            print(f"[{self.node_id}] reject block: invalid PoW")
            return

        # 트랜잭션 검증
        for tx in block.txs:
            ok, reason = self.blockchain.validate_transaction(tx)
            if not ok:
                print(f"[{self.node_id}] reject block: invalid tx {reason}")
                return

        # 블록 적용
        self.blockchain.blocks_by_hash[h] = block
        self.blockchain.height_tip_hash = h
        for tx in block.txs:
            self.blockchain.apply_transaction(tx)
            self.mempool.pop(tx.txid, None)

        print(f"[{self.node_id}] accepted block height={header.height}")
