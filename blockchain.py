"""
블록체인 핵심 로직 모듈
"""
from typing import Dict, List, Tuple, Optional
import time

from crypto import sha256_hex
from models import Block, BlockHeader, Transaction, TxOutput, TxInput
from utxo import UTXOSet
from wallet import Wallet
from utils import merkle_root
from db import block_db, utxo_db

# 난이도 설정
TARGET_HEX = "00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
MAX_TX_PER_BLOCK = 8


class Blockchain:
    """
    블록체인 핵심 클래스
    - 블록 저장 및 관리 (MongoDB 사용)
    - 트랜잭션 검증
    - 블록 채굴 (PoW)
    - 자산 추적
    """

    def __init__(self):
        self.blocks_by_hash: Dict[str, Block] = {}  # 캐시용
        self.height_tip_hash: str = ""  # 최신 블록 해시
        self.utxo = UTXOSet()

        # MongoDB에서 블록체인 로드
        self._load_from_db()

    def _load_from_db(self):
        """MongoDB에서 블록체인 데이터 로드"""
        # 모든 블록 로드
        blocks_data = block_db.get_all_blocks()
        for block_data in blocks_data:
            block = self._block_from_dict(block_data)
            block_hash = block_data["hash"]
            self.blocks_by_hash[block_hash] = block

        # 최신 블록 설정
        tip_data = block_db.get_tip_block()
        if tip_data:
            self.height_tip_hash = tip_data["hash"]

        # UTXO 재구성
        self._rebuild_utxo_from_db()

    def _rebuild_utxo_from_db(self):
        """MongoDB에서 UTXO 재구성"""
        self.utxo = UTXOSet()
        utxos_data = utxo_db.get_all_utxos()
        for utxo_data in utxos_data:
            output = TxOutput(
                asset_id=utxo_data["asset_id"],
                pubkey_hash=utxo_data["pubkey_hash"],
                portion=utxo_data["portion"]
            )
            self.utxo.add_output(utxo_data["txid"], utxo_data["index"], output)

    def _block_to_dict(self, block: Block, block_hash: str) -> dict:
        """Block 객체를 딕셔너리로 변환"""
        txs_list = []
        for tx in block.txs:
            tx_dict = {
                "txid": tx.txid,
                "inputs": [inp.to_dict() for inp in tx.inputs],
                "outputs": [out.to_dict() for out in tx.outputs]
            }
            txs_list.append(tx_dict)

        return {
            "hash": block_hash,
            "height": block.header.height,
            "prev_hash": block.header.prev_hash,
            "merkle_root": block.header.merkle_root,
            "nonce": block.header.nonce,
            "timestamp": int(time.time()),
            "txs": txs_list
        }

    def _block_from_dict(self, data: dict) -> Block:
        """딕셔너리에서 Block 객체 생성"""
        header = BlockHeader(
            height=data["height"],
            prev_hash=data["prev_hash"],
            merkle_root=data["merkle_root"],
            nonce=data["nonce"]
        )

        txs = []
        for tx_data in data["txs"]:
            inputs = [
                TxInput(
                    txid_ref=inp["txid_ref"],
                    index=inp["index"],
                    pubkey=inp["pubkey"],
                    signature=inp["signature"]
                )
                for inp in tx_data["inputs"]
            ]
            outputs = [
                TxOutput(
                    asset_id=out["asset_id"],
                    pubkey_hash=out["pubkey_hash"],
                    portion=out["portion"]
                )
                for out in tx_data["outputs"]
            ]
            tx = Transaction(inputs=inputs, outputs=outputs)
            txs.append(tx)

        return Block(header=header, txs=txs)

    @property
    def tip(self) -> Optional[Block]:
        """현재 체인의 최신 블록"""
        return self.blocks_by_hash.get(self.height_tip_hash)

    def add_genesis_block(self, block: Block):
        """제네시스 블록 추가"""
        h = block.header.hash()
        self.blocks_by_hash[h] = block
        self.height_tip_hash = h

        # MongoDB에 저장
        block_dict = self._block_to_dict(block, h)
        block_db.insert_block(h, block_dict)

        # 모든 출력을 UTXO에 추가
        for tx in block.txs:
            for idx, out in enumerate(tx.outputs):
                self.utxo.add_output(tx.txid, idx, out)
                # MongoDB에 UTXO 저장
                utxo_db.insert_utxo(tx.txid, idx, {
                    "asset_id": out.asset_id,
                    "pubkey_hash": out.pubkey_hash,
                    "portion": out.portion
                })

    def validate_transaction(self, tx: Transaction) -> Tuple[bool, str]:
        """
        트랜잭션 검증
        1. 입력 UTXO 존재 확인
        2. 동일 자산 확인
        3. 입출력 비율 합 일치
        4. 서명 검증
        """
        # 코인베이스 트랜잭션 (제네시스)
        if not tx.inputs:
            return True, "coinbase/genesis tx"

        asset_id = None
        total_in = 0

        # 입력 검증
        for inp in tx.inputs:
            utxo = self.utxo.get_output(inp.txid_ref, inp.index)
            if utxo is None:
                return False, f"missing UTXO for ({inp.txid_ref}, {inp.index})"

            if asset_id is None:
                asset_id = utxo.asset_id
            elif utxo.asset_id != asset_id:
                return False, "multiple asset_ids in inputs"

            total_in += utxo.portion

            # 공개키 해시 확인
            if sha256_hex(bytes.fromhex(inp.pubkey)) != utxo.pubkey_hash:
                return False, "pubkey hash mismatch"

        # 출력 검증
        total_out = 0
        for out in tx.outputs:
            if out.asset_id != asset_id:
                return False, "output asset_id mismatch"
            total_out += out.portion

        if total_in != total_out:
            return False, f"portion mismatch: in={total_in}, out={total_out}"

        # 서명 검증
        msg_hash = tx.message_hash()
        for inp in tx.inputs:
            ok = Wallet.verify(inp.pubkey, msg_hash, inp.signature)
            if not ok:
                return False, "signature verification failed"

        return True, "ok"

    def apply_transaction(self, tx: Transaction):
        """
        검증된 트랜잭션을 UTXO 집합에 적용
        - 입력 UTXO 제거
        - 출력 UTXO 추가
        """
        # 입력 UTXO 제거 (메모리 + DB)
        for inp in tx.inputs:
            self.utxo.remove_output(inp.txid_ref, inp.index)
            utxo_db.delete_utxo(inp.txid_ref, inp.index)

        # 출력 UTXO 추가 (메모리 + DB)
        for idx, out in enumerate(tx.outputs):
            self.utxo.add_output(tx.txid, idx, out)
            utxo_db.insert_utxo(tx.txid, idx, {
                "asset_id": out.asset_id,
                "pubkey_hash": out.pubkey_hash,
                "portion": out.portion
            })

    def mine_block(self, pending_txs: List[Transaction]) -> Block:
        """
        블록 채굴 (PoW)
        - 유효한 트랜잭션 선택
        - 머클 루트 계산
        - nonce 찾기 (난이도 조건 만족)
        """
        # 유효한 트랜잭션 선택
        selected: List[Transaction] = []
        for tx in pending_txs:
            ok, _ = self.validate_transaction(tx)
            if ok:
                selected.append(tx)
            if len(selected) >= MAX_TX_PER_BLOCK:
                break

        if not selected:
            raise RuntimeError("no valid transactions to mine")

        txids = [tx.txid for tx in selected]
        root = merkle_root(txids)

        height = 0
        prev_hash = "0" * 64
        if self.tip is not None:
            height = self.tip.header.height + 1
            prev_hash = self.tip.header.hash()

        # PoW: nonce 찾기
        nonce = 0
        target_int = int(TARGET_HEX, 16)
        while True:
            header = BlockHeader(height=height, prev_hash=prev_hash, merkle_root=root, nonce=nonce)
            h = header.hash()
            if int(h, 16) < target_int:
                # 채굴 성공
                block = Block(header=header, txs=selected)
                self.blocks_by_hash[h] = block
                self.height_tip_hash = h

                # MongoDB에 블록 저장
                block_dict = self._block_to_dict(block, h)
                block_db.insert_block(h, block_dict)

                # 트랜잭션 적용 (UTXO 업데이트 + DB 저장)
                for tx in selected:
                    self.apply_transaction(tx)

                return block
            nonce += 1

    def trace_asset(self, asset_id: str) -> List[Tuple[int, str, Transaction]]:
        """
        특정 자산의 거래 내역 추적
        반환: [(block_height, block_hash, tx), ...] (최신순)
        """
        res = []
        blocks = list(self.blocks_by_hash.items())
        blocks.sort(key=lambda kv: kv[1].header.height, reverse=True)

        for bh, blk in blocks:
            for tx in blk.txs:
                for out in tx.outputs:
                    if out.asset_id == asset_id:
                        res.append((blk.header.height, bh, tx))
                        break
        return res

    def find_output_in_chain(self, txid: str, index: int) -> Optional:
        """체인에서 특정 txid, index의 출력 찾기"""
        for blk in self.blocks_by_hash.values():
            for tx in blk.txs:
                if tx.txid == txid:
                    if 0 <= index < len(tx.outputs):
                        return tx.outputs[index]
        return None

    def build_chain_from_tip(self) -> List[Tuple[str, Block]]:
        """
        tip부터 제네시스까지 체인 구성
        반환: [(hash, block), ...] (tip -> genesis)
        """
        chain: List[Tuple[str, Block]] = []
        cur_hash = self.height_tip_hash
        visited = set()

        while cur_hash and cur_hash not in visited:
            visited.add(cur_hash)
            blk = self.blocks_by_hash.get(cur_hash)
            if blk is None:
                break
            chain.append((cur_hash, blk))
            if blk.header.prev_hash == "0" * 64:
                break
            cur_hash = blk.header.prev_hash

        return chain
