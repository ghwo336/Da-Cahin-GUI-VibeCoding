"""
유틸리티 함수 모듈
"""
import random
from typing import List, Optional

from crypto import sha256_bytes, sha256_hex
from models import Transaction, TxInput, TxOutput, Block, BlockHeader
from wallet import Wallet


def merkle_root(txids: List[str]) -> str:
    """
    트랜잭션 ID 리스트로부터 머클 루트 계산
    """
    if not txids:
        return sha256_hex(b"")
    level = [bytes.fromhex(txid) for txid in txids]
    while len(level) > 1:
        new_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            if i + 1 < len(level):
                right = level[i + 1]
            else:
                right = left  # 마지막 노드 복제
            new_level.append(sha256_bytes(left + right))
        level = new_level
    return level[0].hex()


def create_genesis(num_assets: int, initial_wallets: List[Wallet]) -> Block:
    """
    제네시스 블록 생성
    각 자산은 100% 비율로 초기 지갑에 할당됨
    """
    txs: List[Transaction] = []
    for i in range(num_assets):
        asset_id = f"asset-{i}"
        w = initial_wallets[i]
        out = TxOutput(asset_id=asset_id, pubkey_hash=w.pubkey_hash, portion=100)
        tx = Transaction(inputs=[], outputs=[out])
        txs.append(tx)
    root = merkle_root([tx.txid for tx in txs])
    header = BlockHeader(height=0, prev_hash="0" * 64, merkle_root=root, nonce=0)
    return Block(header=header, txs=txs)


def create_random_valid_tx(blockchain, wallets: List[Wallet]) -> Optional[Transaction]:
    """
    랜덤한 UTXO를 선택하여 유효한 트랜잭션 생성
    """
    utxos = list(blockchain.utxo.all_utxos().items())
    if not utxos:
        return None

    # 랜덤 UTXO 선택
    (txid_ref, idx), utxo = random.choice(utxos)
    asset_id = utxo.asset_id
    portion_total = utxo.portion

    # 출력 개수 결정 (1~3개)
    k = random.randint(1, 3)
    outs: List[TxOutput] = []
    remaining = portion_total

    for i in range(k):
        w = random.choice(wallets)
        if i == k - 1:
            p = remaining
        else:
            p = random.randint(1, remaining - (k - i - 1))
        remaining -= p
        outs.append(TxOutput(asset_id=asset_id, pubkey_hash=w.pubkey_hash, portion=p))

    # UTXO 소유자 지갑 찾기
    owner_wallet = None
    for w in wallets:
        if w.pubkey_hash == utxo.pubkey_hash:
            owner_wallet = w
            break
    if owner_wallet is None:
        return None

    # 서명 생성
    dummy_inp = TxInput(txid_ref=txid_ref, index=idx, pubkey=owner_wallet.pubkey_hex, signature="")
    tx_tmp = Transaction(inputs=[dummy_inp], outputs=outs)
    msg_hash = tx_tmp.message_hash()
    sig = owner_wallet.sign(msg_hash)

    tx_input = TxInput(txid_ref=txid_ref, index=idx, pubkey=owner_wallet.pubkey_hex, signature=sig)
    return Transaction(inputs=[tx_input], outputs=outs)


def create_random_invalid_tx(blockchain, wallets: List[Wallet]) -> Optional[Transaction]:
    """
    의도적으로 무효한 트랜잭션 생성 (테스트용)
    """
    base = create_random_valid_tx(blockchain, wallets)
    if base is None:
        return None

    # 복사본 생성
    tx = Transaction(
        inputs=[TxInput(i.txid_ref, i.index, i.pubkey, i.signature) for i in base.inputs],
        outputs=[TxOutput(o.asset_id, o.pubkey_hash, o.portion) for o in base.outputs],
    )

    # 랜덤하게 오류 주입
    mode = random.choice(["portion", "asset", "pubkey", "signature"])

    if mode == "portion":
        if tx.outputs:
            tx.outputs[0].portion += 1
    elif mode == "asset":
        tx.outputs[0].asset_id = "broken-asset"
    elif mode == "pubkey":
        fake_w = random.choice(wallets)
        tx.inputs[0].pubkey = fake_w.pubkey_hex
    elif mode == "signature":
        fake_w = random.choice(wallets)
        msg_hash = tx.message_hash()
        tx.inputs[0].signature = fake_w.sign(msg_hash)

    tx.txid = tx.compute_txid()
    return tx
