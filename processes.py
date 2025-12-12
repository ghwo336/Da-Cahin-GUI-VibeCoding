"""
유저 프로세스 및 마스터 프로세스 모듈
"""
import time
import random
import threading
from typing import List, Optional

from blockchain import Blockchain, TARGET_HEX
from models import Block
from wallet import Wallet
from crypto import sha256_hex
from utils import create_random_valid_tx, create_random_invalid_tx


class UserProcess(threading.Thread):
    """
    랜덤 트랜잭션 생성 프로세스
    - 일정 비율로 유효/무효 트랜잭션 생성
    - 랜덤 노드로 전송
    """

    def __init__(self, nodes: List, blockchain: Blockchain,
                 wallets: List[Wallet], invalid_ratio: float = 0.2, interval: float = 0.5):
        super().__init__(daemon=True)
        self.nodes = nodes
        self.blockchain = blockchain
        self.wallets = wallets
        self.invalid_ratio = invalid_ratio
        self.interval = interval
        self.running = False

    def run(self):
        self.running = True
        print("[userProcess] started")
        while self.running:
            if not self.nodes:
                time.sleep(self.interval)
                continue

            node = random.choice(self.nodes)

            # 랜덤하게 유효/무효 트랜잭션 생성
            if random.random() < self.invalid_ratio:
                tx = create_random_invalid_tx(self.blockchain, self.wallets)
            else:
                tx = create_random_valid_tx(self.blockchain, self.wallets)

            if tx is not None:
                print(f"[userProcess] send tx {tx.txid[:8]} to {node.node_id}")
                node.receive_transaction(tx)

            time.sleep(self.interval)

    def stop(self):
        self.running = False
        print("[userProcess] stopping...")


class MasterProcess:
    """
    마스터 프로세스 - 네트워크 전체 관리 및 모니터링
    - 노드 관리
    - 트랜잭션 검증
    - 체인 스냅샷
    - 자산 추적
    """

    def __init__(self, nodes: List, blockchain: Blockchain):
        self.nodes = nodes
        self.blockchain = blockchain

    def find_node(self, node_id: str) -> Optional:
        """노드 ID로 노드 찾기"""
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def on_block_mined(self, node, block: Block):
        """
        블록 채굴 이벤트 핸들러
        - 채굴 정보 출력
        - 첫 번째 트랜잭션 자동 검증
        """
        now = time.strftime("%H:%M:%S")
        h = block.header
        bhash = h.hash()
        print(f"[master] a block with blockHeight {h.height} mined by {node.node_id} (report arrived at {now})")

        target_int = int(TARGET_HEX, 16)
        print(f"         headerHash={bhash}, target={TARGET_HEX}, ok={int(bhash,16) < target_int}")

        # 첫 번째 트랜잭션 검증
        if block.txs:
            print("         verifying leftmost tx in Merkle-tree:")
            self.verify_transaction(node.node_id, from_last_block=True)

    def verify_transaction(self, node_id: str, from_last_block: bool = False):
        """
        트랜잭션 검증 프로세스 상세 출력
        - 입력 outpoint 확인
        - 공개키 해시 확인
        - 서명 확인
        - 입출력 비율 확인
        """
        node = self.find_node(node_id)
        if node is None:
            print(f"[master] no such node {node_id}")
            return

        blk = node.last_mined_block if from_last_block else node.blockchain.tip
        if blk is None or not blk.txs:
            print(f"[master] node {node_id} has no mined block / no txs")
            return

        tx = blk.txs[0]
        print(f"F{node_id} 의 Merkle-tree leftmost txID: {tx.txid}")

        asset_id = None
        total_in = 0

        # 각 입력 검증
        for idx, inp in enumerate(tx.inputs):
            print(f"  input#{idx}: outpoint = ({inp.txid_ref}, {inp.index})")
            utxo = self.blockchain.find_output_in_chain(inp.txid_ref, inp.index)

            if utxo is None:
                print("    check - outpoint ... NO! (output not found in chain)")
                return

            print(f"    outpoint: <asset={utxo.asset_id}>, <pubKHash={utxo.pubkey_hash[:8]}...>, <portion={utxo.portion}>")

            if asset_id is None:
                asset_id = utxo.asset_id
            elif utxo.asset_id != asset_id:
                print("    check - same assetId ... NO! (mixed assets)")
                return

            total_in += utxo.portion

            # 공개키 해시 확인
            calc_hash = sha256_hex(bytes.fromhex(inp.pubkey))
            print(f"    check - <pubK> vs <pubKHash> ... {'yes!' if calc_hash == utxo.pubkey_hash else 'NO!'}")

            # 서명 확인
            msg_hash = tx.message_hash()
            from wallet import Wallet
            ok_sig = Wallet.verify(inp.pubkey, msg_hash, inp.signature)
            print(f"    check - <pubK> <sig> txid ... {'yes!' if ok_sig else 'NO!'}")

            if not ok_sig:
                return

        # 출력 검증
        total_out = 0
        for o in tx.outputs:
            if o.asset_id != asset_id:
                print("  check - all outputs assetId equal input assetId ... NO!")
                return
            total_out += o.portion

        print(f"  check - sum(in portion) == sum(out portion) ... "
              f"{'yes!' if total_in == total_out else 'NO!'} (in={total_in}, out={total_out})")

        if total_in != total_out:
            return

        print("  모든 검증 과정 성공적으로 통과: yes!")

    def snapshot_daChain(self, only_node: Optional[str] = None):
        """
        체인 스냅샷 출력
        - ALL: 모든 노드의 체인
        - 특정 노드: 해당 노드의 체인만
        """
        nodes = self.nodes
        if only_node is not None:
            n = self.find_node(only_node)
            if n is None:
                print(f"[master] no such node {only_node}")
                return
            nodes = [n]

        for n in nodes:
            chain = n.blockchain.build_chain_from_tip()
            if not chain:
                print(f"{n.node_id}: <empty chain>")
                continue

            print(f"{n.node_id}: ", end="")
            parts = []
            for bhash, blk in chain:
                parts.append(f"blockHeight {blk.header.height}({bhash[:8]})")
            print("  ".join(parts))

    def trace_asset(self, asset_id: str, limit: Optional[int] = None):
        """
        자산 추적
        - 특정 자산의 모든 거래 내역 출력
        - limit: 출력할 최대 거래 수
        """
        history = self.blockchain.trace_asset(asset_id)
        if limit is not None:
            history = history[:limit]

        if not history:
            print(f"[master] no txs for asset {asset_id}")
            return

        for h, bh, tx in history:
            print(f"[blockHeight {h}, txID: {tx.txid[:8]}..., blockHash: {bh[:8]}...]")
            for i, inp in enumerate(tx.inputs):
                print(f"   input#{i}: ({inp.txid_ref[:8]}..., {inp.index})")
            for j, out in enumerate(tx.outputs):
                print(f"   output#{j}: asset={out.asset_id}, portion={out.portion}, "
                      f"pubKeyHash={out.pubkey_hash[:8]}...")
