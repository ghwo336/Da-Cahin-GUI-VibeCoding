import hashlib
import json
import random
import time
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# =======================
# Crypto / Hash Utilities
# =======================

try:
    from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError
except ImportError:
    SigningKey = None
    VerifyingKey = None
    BadSignatureError = Exception
    SECP256k1 = None


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ================
# Data Structures
# ================

@dataclass
class TxOutput:
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
    inputs: List[TxInput]
    outputs: List[TxOutput]
    txid: str = field(init=False)

    def __post_init__(self):
        # compute txid including signatures
        self.txid = self.compute_txid()

    def _serialize(self, include_signatures: bool = True) -> bytes:
        data = {
            "inputs": [inp.to_dict(include_signature=include_signatures) for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
        }
        s = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return s.encode("utf-8")

    def compute_txid(self) -> str:
        return sha256_hex(self._serialize(include_signatures=True))

    def message_hash(self) -> str:
        """
        Hash used for signing: transaction without signatures.
        (실제 서명에 사용하는 메시지 해시)
        """
        return sha256_hex(self._serialize(include_signatures=False))


@dataclass
class BlockHeader:
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
        s = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256_hex(s)


@dataclass
class Block:
    header: BlockHeader
    txs: List[Transaction]


# =========
# UTXO Set
# =========

class UTXOSet:
    """
    Simple in-memory UTXO set: maps (txid, index) -> TxOutput
    """

    def __init__(self):
        self.utxos: Dict[Tuple[str, int], TxOutput] = {}

    def add_output(self, txid: str, index: int, out: TxOutput):
        self.utxos[(txid, index)] = out

    def remove_output(self, txid: str, index: int):
        self.utxos.pop((txid, index), None)

    def get_output(self, txid: str, index: int) -> Optional[TxOutput]:
        return self.utxos.get((txid, index))

    def all_utxos(self) -> Dict[Tuple[str, int], TxOutput]:
        return dict(self.utxos)


# =================
# Merkle Tree Util
# =================

def merkle_root(txids: List[str]) -> str:
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
                # duplicate last (간단 구현)
                right = left
            new_level.append(sha256_bytes(left + right))
        level = new_level
    return level[0].hex()


# ==============
# Key Management
# ==============

class Wallet:
    """
    Simple wrapper around an ECDSA private/public key pair.
    """

    def __init__(self):
        if SigningKey is None:
            raise RuntimeError("ecdsa library is required. Install with 'python3 -m pip install ecdsa'.")
        self.sk: SigningKey = SigningKey.generate(curve=SECP256k1)
        self.vk: VerifyingKey = self.sk.get_verifying_key()

    @property
    def pubkey_bytes(self) -> bytes:
        return self.vk.to_string()

    @property
    def pubkey_hex(self) -> str:
        return self.pubkey_bytes.hex()

    @property
    def pubkey_hash(self) -> str:
        return sha256_hex(self.pubkey_bytes)

    def sign(self, msg_hash_hex: str) -> str:
        msg_bytes = bytes.fromhex(msg_hash_hex)
        sig = self.sk.sign(msg_bytes)
        return sig.hex()

    @staticmethod
    def verify(pubkey_hex: str, msg_hash_hex: str, signature_hex: str) -> bool:
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


# ==========
# Blockchain
# ==========

# 난이도: 앞에 00000 정도면 로컬에서 충분히 캐짐 (필요하면 0000/000000 등으로 조절)
TARGET_HEX = "00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
MAX_TX_PER_BLOCK = 8


class Blockchain:
    def __init__(self):
        self.blocks_by_hash: Dict[str, Block] = {}
        self.height_tip_hash: str = ""  # hash of tip block
        self.utxo = UTXOSet()

    @property
    def tip(self) -> Optional[Block]:
        return self.blocks_by_hash.get(self.height_tip_hash)

    def add_genesis_block(self, block: Block):
        h = block.header.hash()
        self.blocks_by_hash[h] = block
        self.height_tip_hash = h
        # UTXO: include all outputs of all txs
        for tx in block.txs:
            for idx, out in enumerate(tx.outputs):
                self.utxo.add_output(tx.txid, idx, out)

    def validate_transaction(self, tx: Transaction) -> Tuple[bool, str]:
        # coinbase-like tx (genesis) 처리: input 이 비어있으면 그냥 통과
        if not tx.inputs:
            return True, "coinbase/genesis tx"
        # 1. 모든 input 존재 & 같은 asset
        asset_id = None
        total_in = 0
        for inp in tx.inputs:
            utxo = self.utxo.get_output(inp.txid_ref, inp.index)
            if utxo is None:
                return False, f"missing UTXO for ({inp.txid_ref}, {inp.index})"
            if asset_id is None:
                asset_id = utxo.asset_id
            elif utxo.asset_id != asset_id:
                return False, "multiple asset_ids in inputs"
            total_in += utxo.portion
            # pubkey hash check
            if sha256_hex(bytes.fromhex(inp.pubkey)) != utxo.pubkey_hash:
                return False, "pubkey hash mismatch"
        # 2. outputs asset_id & sum
        total_out = 0
        for out in tx.outputs:
            if out.asset_id != asset_id:
                return False, "output asset_id mismatch"
            total_out += out.portion
        if total_in != total_out:
            return False, f"portion mismatch: in={total_in}, out={total_out}"
        # 3. signature check
        msg_hash = tx.message_hash()
        for inp in tx.inputs:
            ok = Wallet.verify(inp.pubkey, msg_hash, inp.signature)
            if not ok:
                return False, "signature verification failed"
        return True, "ok"

    def apply_transaction(self, tx: Transaction):
        # assumes already validated
        # spend inputs
        for inp in tx.inputs:
            self.utxo.remove_output(inp.txid_ref, inp.index)
        # add outputs
        for idx, out in enumerate(tx.outputs):
            self.utxo.add_output(tx.txid, idx, out)

    def mine_block(self, pending_txs: List[Transaction]) -> Block:
        # pick up to MAX_TX_PER_BLOCK valid txs
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

        nonce = 0
        target_int = int(TARGET_HEX, 16)
        while True:
            header = BlockHeader(height=height, prev_hash=prev_hash, merkle_root=root, nonce=nonce)
            h = header.hash()
            if int(h, 16) < target_int:
                # found
                block = Block(header=header, txs=selected)
                # apply to chain
                self.blocks_by_hash[h] = block
                self.height_tip_hash = h
                for tx in selected:
                    self.apply_transaction(tx)
                return block
            nonce += 1

    def trace_asset(self, asset_id: str) -> List[Tuple[int, str, Transaction]]:
        """
        Return list of (block_height, block_hash, tx) where tx involves given asset_id.
        Newest block first.
        """
        res = []
        # iterate over blocks by height descending
        blocks = list(self.blocks_by_hash.items())
        # sort by header.height
        blocks.sort(key=lambda kv: kv[1].header.height, reverse=True)
        for bh, blk in blocks:
            for tx in blk.txs:
                for out in tx.outputs:
                    if out.asset_id == asset_id:
                        res.append((blk.header.height, bh, tx))
                        break
        return res

    # 마스터 검증용: 체인에서 특정 txid,index의 output 찾기
    def find_output_in_chain(self, txid: str, index: int) -> Optional[TxOutput]:
        for blk in self.blocks_by_hash.values():
            for tx in blk.txs:
                if tx.txid == txid:
                    if 0 <= index < len(tx.outputs):
                        return tx.outputs[index]
        return None

    def build_chain_from_tip(self) -> List[Tuple[str, Block]]:
        """
        tip부터 prev_hash 따라가며 canonical chain (hash, block) 리스트 반환 (tip -> genesis)
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


# ===============
# Full Node (Sim)
# ===============

class MasterProcess:  # 선언 먼저해서 FullNode에서 타입으로 씀
    ...


class FullNode:
    """
    Simplified full node without real TCP networking.
    나중에 send/receive를 소켓으로 바꾸면 실제 P2P로 확장 가능.
    """

    def __init__(self, node_id: str, blockchain: Blockchain, master: Optional["MasterProcess"] = None):
        self.node_id = node_id
        self.blockchain = blockchain
        self.mempool: Dict[str, Transaction] = {}
        self.peers: List["FullNode"] = []
        self.last_mined_block: Optional[Block] = None
        self.master = master

    def connect_peer(self, peer: "FullNode"):
        if peer not in self.peers:
            self.peers.append(peer)

    def receive_transaction(self, tx: Transaction):
        # basic mempool insert & broadcast
        if tx.txid in self.mempool:
            return
        ok, reason = self.blockchain.validate_transaction(tx)
        if not ok:
            print(f"[{self.node_id}] reject tx {tx.txid}: {reason}")
            return
        self.mempool[tx.txid] = tx
        for p in self.peers:
            p.receive_transaction(tx)

    def mine(self):
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
        # clear mempool entries that were included
        for tx in block.txs:
            self.mempool.pop(tx.txid, None)
        # broadcast block (simplified)
        for p in self.peers:
            p.receive_block(block)
        print(f"[{self.node_id}] mined block height={block.header.height}")
        # 마스터에 보고
        if self.master is not None:
            self.master.on_block_mined(self, block)
        return block

    def receive_block(self, block: Block):
        # 아주 단순화: 우리 tip에만 붙여준다 (fork 무시)
        header = block.header
        prev_hash = header.prev_hash
        tip_hash = self.blockchain.height_tip_hash
        # only accept if extends our tip
        if tip_hash and prev_hash != tip_hash:
            # ignore forks in this simple version
            return
        # check PoW
        target_int = int(TARGET_HEX, 16)
        h = header.hash()
        if int(h, 16) >= target_int:
            print(f"[{self.node_id}] reject block: invalid PoW")
            return
        # validate txs
        for tx in block.txs:
            ok, reason = self.blockchain.validate_transaction(tx)
            if not ok:
                print(f"[{self.node_id}] reject block: invalid tx {reason}")
                return
        # apply block to blockchain
        self.blockchain.blocks_by_hash[h] = block
        self.blockchain.height_tip_hash = h
        for tx in block.txs:
            self.blockchain.apply_transaction(tx)
            self.mempool.pop(tx.txid, None)
        print(f"[{self.node_id}] accepted block height={header.height}")


# ======================
# Genesis / Demo Helpers
# ======================

def create_genesis(blockchain: Blockchain, num_assets: int, initial_wallets: List[Wallet]):
    """
    Create genesis block with num_assets assets, each owned 100% by a distinct wallet.
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
    genesis_block = Block(header=header, txs=txs)
    blockchain.add_genesis_block(genesis_block)
    print(f"[genesis] created with {num_assets} assets")


def create_random_valid_tx(blockchain: Blockchain, wallets: List[Wallet]) -> Optional[Transaction]:
    """
    Pick random UTXO of a single asset, create transaction redistributing its portion
    to random wallets.
    """
    utxos = list(blockchain.utxo.all_utxos().items())
    if not utxos:
        return None
    # pick random utxo
    (txid_ref, idx), utxo = random.choice(utxos)
    asset_id = utxo.asset_id
    portion_total = utxo.portion

    # decide number of outputs (1~3)
    k = random.randint(1, 3)
    # pick random wallets as new owners
    outs: List[TxOutput] = []
    remaining = portion_total
    for i in range(k):
        w = random.choice(wallets)
        if i == k - 1:
            p = remaining
        else:
            p = random.randint(1, remaining - (k - i - 1))  # leave at least 1 for each remaining
        remaining -= p
        outs.append(TxOutput(asset_id=asset_id, pubkey_hash=w.pubkey_hash, portion=p))

    # build tx without signatures first
    # need owner wallet of the chosen utxo (find wallet with matching pubkey_hash)
    owner_wallet = None
    for w in wallets:
        if w.pubkey_hash == utxo.pubkey_hash:
            owner_wallet = w
            break
    if owner_wallet is None:
        return None

    dummy_inp = TxInput(txid_ref=txid_ref, index=idx, pubkey=owner_wallet.pubkey_hex, signature="")
    tx_tmp = Transaction(inputs=[dummy_inp], outputs=outs)
    msg_hash = tx_tmp.message_hash()
    sig = owner_wallet.sign(msg_hash)
    tx_input = TxInput(txid_ref=txid_ref, index=idx, pubkey=owner_wallet.pubkey_hex, signature=sig)
    tx = Transaction(inputs=[tx_input], outputs=outs)
    return tx


def create_random_invalid_tx(blockchain: Blockchain, wallets: List[Wallet]) -> Optional[Transaction]:
    """
    유효 tx를 하나 만든 다음 일부 필드를 깨서 invalid tx 생성.
    """
    base = create_random_valid_tx(blockchain, wallets)
    if base is None:
        return None
    # deep-ish copy
    tx = Transaction(
        inputs=[TxInput(i.txid_ref, i.index, i.pubkey, i.signature) for i in base.inputs],
        outputs=[TxOutput(o.asset_id, o.pubkey_hash, o.portion) for o in base.outputs],
    )

    mode = random.choice(["portion", "asset", "pubkey", "signature"])

    if mode == "portion":
        # in/out 잔고 틀리게
        if tx.outputs:
            tx.outputs[0].portion += 1
    elif mode == "asset":
        # output asset_id 변경
        tx.outputs[0].asset_id = "broken-asset"
    elif mode == "pubkey":
        # input pubkey를 랜덤으로 변경 → pubkey_hash mismatch
        fake_w = random.choice(wallets)
        tx.inputs[0].pubkey = fake_w.pubkey_hex
    elif mode == "signature":
        # 서명을 다른 키로 다시
        fake_w = random.choice(wallets)
        msg_hash = tx.message_hash()
        tx.inputs[0].signature = fake_w.sign(msg_hash)

    # txid 다시 계산
    tx.txid = tx.compute_txid()
    return tx


# =================
# User & Master
# =================

class UserProcess(threading.Thread):
    """
    랜덤 트랜잭션을 생성해서 노드로 보내는 쓰레드.
    invalid_ratio 비율로 일부 트랜잭션은 고의로 invalid.
    """

    def __init__(self, nodes: List[FullNode], blockchain: Blockchain,
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
    과제에서 말하는 masterProcess 역할.
    - 노드 리스트 보유
    - verify-transaction
    - snapshot daChain
    - trace <assetID>
    - 블록 채굴 보고 출력
    """

    def __init__(self, nodes: List[FullNode], blockchain: Blockchain):
        self.nodes = nodes
        self.blockchain = blockchain

    def find_node(self, node_id: str) -> Optional[FullNode]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    # 블록 채굴 시 노드가 호출
    def on_block_mined(self, node: FullNode, block: Block):
        now = time.strftime("%H:%M:%S")
        h = block.header
        bhash = h.hash()
        print(f"[master] a block with blockHeight {h.height} mined by {node.node_id} (report arrived at {now})")
        target_int = int(TARGET_HEX, 16)
        print(f"         headerHash={bhash}, target={TARGET_HEX}, ok={int(bhash,16) < target_int}")
        # 첫 번째 tx 검증 과정도 바로 보여줄 수 있음
        if block.txs:
            print("         verifying leftmost tx in Merkle-tree:")
            self.verify_transaction(node.node_id, from_last_block=True)

    def verify_transaction(self, node_id: str, from_last_block: bool = False):
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

        # 입력 outpoint 기반으로 체인에서 output 가져와서 검증 과정 로그 출력
        asset_id = None
        total_in = 0
        # 1. 각 input 확인
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
            # pubkey hash
            calc_hash = sha256_hex(bytes.fromhex(inp.pubkey))
            print(f"    check - <pubK> vs <pubKHash> ... {'yes!' if calc_hash == utxo.pubkey_hash else 'NO!'}")
            # signature
            msg_hash = tx.message_hash()
            ok_sig = Wallet.verify(inp.pubkey, msg_hash, inp.signature)
            print(f"    check - <pubK> <sig> txid ... {'yes!' if ok_sig else 'NO!'}")
            if not ok_sig:
                return

        # 2. output 자산/합 체크
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
        snapshot daChain ALL / snapshot daChain F0
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
            # tip -> genesis
            parts = []
            for bhash, blk in chain:
                parts.append(f"blockHeight {blk.header.height}({bhash[:8]})")
            print("  ".join(parts))

    def trace_asset(self, asset_id: str, limit: Optional[int] = None):
        """
        trace <assetID> ALL / trace <assetID> k
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


# ================
# CLI / Main Logic
# ================

def run_cli():
    random.seed(0)

    blockchain: Optional[Blockchain] = None
    wallets: List[Wallet] = []
    nodes: List[FullNode] = []
    user_proc: Optional[UserProcess] = None
    master: Optional[MasterProcess] = None

    print("=== daChain CLI (simplified single-process demo) ===")
    print("명령 예시:")
    print("  initiate daChain 8")
    print("  initiate fullNodes 5")
    print("  run userProcess")
    print("  stop userProcess")
    print("  mine F0")
    print("  verify-transaction F0")
    print("  snapshot daChain ALL")
    print("  snapshot daChain F0")
    print("  trace asset-0 ALL")
    print("  trace asset-0 5")
    print("  exit")

    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue

        if cmd == "exit":
            if user_proc is not None:
                user_proc.stop()
            break

        parts = cmd.split()
        if parts[0] == "initiate" and len(parts) >= 3 and parts[1] == "daChain":
            # initiate daChain N
            if blockchain is not None:
                print("이미 daChain 이 초기화되어 있습니다.")
                continue
            try:
                N = int(parts[2])
            except ValueError:
                print("N 은 정수여야 합니다.")
                continue
            blockchain = Blockchain()
            # 최초 등록용 N개 + 추가 참여자 N개 해서 총 2N 지갑 생성
            wallets = [Wallet() for _ in range(2 * N)]
            create_genesis(blockchain, num_assets=N, initial_wallets=wallets[:N])
            print(f"지갑 총 {len(wallets)}개 생성 (초기 소유자 {N}, 추가 참여자 {N})")

        elif parts[0] == "initiate" and len(parts) >= 3 and parts[1] == "fullNodes":
            # initiate fullNodes L
            if blockchain is None:
                print("먼저 initiate daChain N 을 실행하세요.")
                continue
            if nodes:
                print("이미 fullNodes 가 초기화되어 있습니다.")
                continue
            try:
                L = int(parts[2])
            except ValueError:
                print("L 은 정수여야 합니다.")
                continue
            # 단순히 모두 같은 blockchain 공유 (멀티 체인/포크까지는 시뮬레이트 안 함)
            nodes = []
            master = MasterProcess(nodes, blockchain)
            for i in range(L):
                node = FullNode(f"F{i}", blockchain, master=master)
                nodes.append(node)
            # 풀 그래프로 연결 (원래는 random graph + connected 체크)
            for i in range(L):
                for j in range(i + 1, L):
                    nodes[i].connect_peer(nodes[j])
                    nodes[j].connect_peer(nodes[i])
            print(f"{L} 개의 full node 생성 및 상호 연결 완료.")

        elif parts[0] == "run" and len(parts) >= 2 and parts[1] == "userProcess":
            if blockchain is None or not nodes or not wallets:
                print("먼저 daChain 과 fullNodes 를 초기화하세요.")
                continue
            if user_proc is not None and user_proc.running:
                print("userProcess 가 이미 실행 중입니다.")
                continue
            user_proc = UserProcess(nodes=nodes, blockchain=blockchain, wallets=wallets, invalid_ratio=0.2, interval=0.5)
            user_proc.start()

        elif parts[0] == "stop" and len(parts) >= 2 and parts[1] == "userProcess":
            if user_proc is None or not user_proc.running:
                print("userProcess 가 실행 중이 아닙니다.")
                continue
            user_proc.stop()

        elif parts[0] == "mine" and len(parts) == 2:
            # mine F0
            nid = parts[1]
            node = None
            for n in nodes:
                if n.node_id == nid:
                    node = n
                    break
            if node is None:
                print(f"no such node {nid}")
                continue
            node.mine()

        elif parts[0] == "verify-transaction" and len(parts) == 2:
            if master is None:
                print("masterProcess 가 아직 없습니다. 먼저 fullNodes 를 초기화하세요.")
                continue
            nid = parts[1]
            master.verify_transaction(nid)

        elif parts[0] == "snapshot" and len(parts) >= 3 and parts[1] == "daChain":
            if master is None:
                print("masterProcess 가 아직 없습니다.")
                continue
            # snapshot daChain ALL or snapshot daChain F0
            if parts[2] == "ALL":
                master.snapshot_daChain()
            else:
                master.snapshot_daChain(parts[2])

        elif parts[0] == "trace" and len(parts) >= 2:
            if master is None:
                print("masterProcess 가 아직 없습니다.")
                continue
            asset_id = parts[1]
            if len(parts) == 3:
                if parts[2] == "ALL":
                    master.trace_asset(asset_id, limit=None)
                else:
                    try:
                        k = int(parts[2])
                    except ValueError:
                        print("k 는 정수이거나 ALL 이어야 합니다.")
                        continue
                    master.trace_asset(asset_id, limit=k)
            else:
                master.trace_asset(asset_id, limit=None)

        else:
            print("알 수 없는 명령입니다.")


if __name__ == "__main__":
    if SigningKey is None:
        print("This demo requires the 'ecdsa' package. Install with: python3 -m pip install ecdsa")
    else:
        run_cli()