"""
DaBlockChain Web Application
Flask 기반 블록체인 웹 인터페이스
"""
from flask import Flask, render_template, request, jsonify, session
import secrets
from typing import Dict, List, Optional
import threading

from blockchain import Blockchain
from wallet import Wallet
from models import Transaction, TxInput, TxOutput
from utils import create_genesis
from crypto import sha256_hex
from db import init_database, wallet_db, block_db
import time

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# 전역 상태
blockchain = Blockchain()
wallets: Dict[str, Wallet] = {}  # 메모리 캐시
pending_txs: List[Transaction] = []
mining_status = {"is_mining": False, "log": []}


def load_wallets_from_db():
    """MongoDB에서 지갑 로드"""
    from crypto import SigningKey, SECP256k1
    wallets_data = wallet_db.get_all_wallets()
    for wallet_data in wallets_data:
        wallet = Wallet.__new__(Wallet)  # __init__ 건너뛰기
        wallet.sk = SigningKey.from_string(bytes.fromhex(wallet_data["privkey"]), curve=SECP256k1)
        wallet.vk = wallet.sk.get_verifying_key()
        wallets[wallet_data["name"]] = wallet


def initialize_genesis():
    """제네시스 블록 초기화"""
    num_assets = 5
    initial_wallets = []

    for i in range(num_assets):
        wallet = Wallet()
        wallet_name = f"genesis-wallet-{i}"
        wallets[wallet_name] = wallet
        initial_wallets.append(wallet)

        # MongoDB에 지갑 저장
        wallet_db.insert_wallet(wallet_name, {
            "privkey": wallet.sk.to_string().hex(),
            "pubkey": wallet.pubkey_hex,
            "pubkey_hash": wallet.pubkey_hash
        })

    genesis_block = create_genesis(num_assets, initial_wallets)
    blockchain.add_genesis_block(genesis_block)

    return f"Genesis block created with {num_assets} assets"


def get_balance(wallet: Wallet) -> Dict[str, int]:
    """지갑의 잔액 계산"""
    balances: Dict[str, int] = {}
    for (txid, idx), utxo in blockchain.utxo.all_utxos().items():
        if utxo.pubkey_hash == wallet.pubkey_hash:
            if utxo.asset_id not in balances:
                balances[utxo.asset_id] = 0
            balances[utxo.asset_id] += utxo.portion
    return balances


def create_transfer_tx(wallet: Wallet, to_pubkey_hash: str, asset_id: str, portion: int) -> Transaction:
    """트랜잭션 생성"""
    inputs_list = []
    total_in = 0

    for (txid, idx), utxo in blockchain.utxo.all_utxos().items():
        if utxo.pubkey_hash == wallet.pubkey_hash and utxo.asset_id == asset_id:
            inputs_list.append((txid, idx, utxo))
            total_in += utxo.portion

    if not inputs_list:
        raise ValueError(f"No UTXO found for asset {asset_id}")

    if total_in < portion:
        raise ValueError(f"Insufficient balance: have {total_in}, need {portion}")

    outputs = [TxOutput(asset_id=asset_id, pubkey_hash=to_pubkey_hash, portion=portion)]

    if total_in > portion:
        outputs.append(TxOutput(asset_id=asset_id, pubkey_hash=wallet.pubkey_hash, portion=total_in - portion))

    inputs = []
    for txid, idx, _ in inputs_list:
        dummy_inp = TxInput(txid_ref=txid, index=idx, pubkey=wallet.pubkey_hex, signature="")
        inputs.append(dummy_inp)

    tx_tmp = Transaction(inputs=inputs, outputs=outputs)
    msg_hash = tx_tmp.message_hash()

    signed_inputs = []
    for txid, idx, _ in inputs_list:
        sig = wallet.sign(msg_hash)
        signed_inputs.append(TxInput(txid_ref=txid, index=idx, pubkey=wallet.pubkey_hex, signature=sig))

    return Transaction(inputs=signed_inputs, outputs=outputs)


# ==================== Routes ====================

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    """지갑 목록 조회"""
    wallet_list = []
    current_wallet = session.get('current_wallet')

    for name, wallet in wallets.items():
        wallet_list.append({
            'name': name,
            'pubkey_hash': wallet.pubkey_hash,
            'selected': name == current_wallet
        })

    return jsonify(wallet_list)


@app.route('/api/wallets', methods=['POST'])
def create_wallet():
    """지갑 생성"""
    data = request.json
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Wallet name is required'}), 400

    if wallet_db.wallet_exists(name):
        return jsonify({'error': f'Wallet "{name}" already exists'}), 400

    wallet = Wallet()
    wallets[name] = wallet

    # MongoDB에 저장
    wallet_db.insert_wallet(name, {
        "privkey": wallet.sk.to_string().hex(),
        "pubkey": wallet.pubkey_hex,
        "pubkey_hash": wallet.pubkey_hash
    })

    return jsonify({
        'message': f'Wallet "{name}" created successfully',
        'pubkey_hash': wallet.pubkey_hash
    })


@app.route('/api/wallets/select', methods=['POST'])
def select_wallet():
    """지갑 선택"""
    data = request.json
    name = data.get('name', '').strip()

    if name not in wallets:
        return jsonify({'error': f'Wallet "{name}" not found'}), 404

    session['current_wallet'] = name
    return jsonify({'message': f'Selected wallet: {name}'})


@app.route('/api/wallets/balance', methods=['GET'])
def check_balance():
    """잔액 확인"""
    wallet_name = request.args.get('name') or session.get('current_wallet')

    if not wallet_name or wallet_name not in wallets:
        return jsonify({'error': 'No wallet selected'}), 400

    wallet = wallets[wallet_name]
    balances = get_balance(wallet)

    return jsonify({
        'wallet_name': wallet_name,
        'pubkey_hash': wallet.pubkey_hash,
        'balances': balances
    })


@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    """블록체인 조회"""
    chain = blockchain.build_chain_from_tip()
    chain.reverse()

    blocks = []
    for block_hash, block in chain:
        # MongoDB에서 timestamp 가져오기
        block_data = block_db.get_block_by_hash(block_hash)
        timestamp = block_data.get('timestamp') if block_data else int(time.time())

        blocks.append({
            'height': block.header.height,
            'hash': block_hash,
            'prev_hash': block.header.prev_hash,
            'merkle_root': block.header.merkle_root,
            'nonce': block.header.nonce,
            'tx_count': len(block.txs),
            'timestamp': timestamp,
            'difficulty': 4
        })

    return jsonify(blocks)


@app.route('/api/blockchain/block/<int:height>', methods=['GET'])
def get_block_details(height):
    """블록 상세 정보"""
    chain = blockchain.build_chain_from_tip()

    for block_hash, block in chain:
        if block.header.height == height:
            txs = []
            for tx in block.txs:
                outputs = []
                for out in tx.outputs:
                    outputs.append({
                        'asset_id': out.asset_id,
                        'pubkey_hash': out.pubkey_hash,
                        'portion': out.portion
                    })

                txs.append({
                    'txid': tx.txid,
                    'inputs': len(tx.inputs),
                    'outputs': outputs
                })

            return jsonify({
                'height': block.header.height,
                'hash': block_hash,
                'prev_hash': block.header.prev_hash,
                'merkle_root': block.header.merkle_root,
                'nonce': block.header.nonce,
                'transactions': txs
            })

    return jsonify({'error': 'Block not found'}), 404


@app.route('/api/transactions/pending', methods=['GET'])
def get_pending_txs():
    """펜딩 트랜잭션 조회"""
    txs = []
    for tx in pending_txs:
        outputs = []
        for out in tx.outputs:
            outputs.append({
                'asset_id': out.asset_id,
                'pubkey_hash': out.pubkey_hash,
                'portion': out.portion
            })

        txs.append({
            'txid': tx.txid,
            'inputs': len(tx.inputs),
            'outputs': outputs
        })

    return jsonify(txs)


@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    """트랜잭션 생성"""
    wallet_name = session.get('current_wallet')

    if not wallet_name or wallet_name not in wallets:
        return jsonify({'error': 'No wallet selected'}), 400

    data = request.json
    to_pubkey_hash = data.get('to_pubkey_hash', '').strip()
    asset_id = data.get('asset_id', '').strip()
    portion = data.get('portion')

    if not to_pubkey_hash or not asset_id or not portion:
        return jsonify({'error': 'All fields are required'}), 400

    try:
        portion = int(portion)
        if portion <= 0 or portion > 100:
            raise ValueError('Portion must be between 1 and 100')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    wallet = wallets[wallet_name]

    try:
        tx = create_transfer_tx(wallet, to_pubkey_hash, asset_id, portion)
        pending_txs.append(tx)
        return jsonify({
            'message': 'Transaction created successfully',
            'txid': tx.txid
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/mine', methods=['POST'])
def start_mining():
    """마이닝 시작"""
    global mining_status

    if mining_status['is_mining']:
        return jsonify({'error': 'Mining already in progress'}), 400

    if not pending_txs:
        return jsonify({'error': 'No pending transactions to mine'}), 400

    def mine():
        global mining_status
        mining_status['is_mining'] = True
        mining_status['log'] = []

        mining_status['log'].append('Starting mining process...')
        mining_status['log'].append(f'Pending transactions: {len(pending_txs)}')

        try:
            block = blockchain.mine_block(pending_txs)

            mined_txids = {tx.txid for tx in block.txs}
            pending_txs[:] = [tx for tx in pending_txs if tx.txid not in mined_txids]

            mining_status['log'].append('Block mined successfully!')
            mining_status['log'].append(f'  Height: {block.header.height}')
            mining_status['log'].append(f'  Hash: {block.header.hash()}')
            mining_status['log'].append(f'  Nonce: {block.header.nonce}')
            mining_status['log'].append(f'  Transactions: {len(block.txs)}')
            mining_status['log'].append(f'  Remaining pending: {len(pending_txs)}')
        except Exception as e:
            mining_status['log'].append(f'Mining failed: {e}')
        finally:
            mining_status['is_mining'] = False

    thread = threading.Thread(target=mine, daemon=True)
    thread.start()

    return jsonify({'message': 'Mining started'})


@app.route('/api/mine/status', methods=['GET'])
def get_mining_status():
    """마이닝 상태 조회"""
    return jsonify(mining_status)


@app.route('/api/trace/<asset_id>', methods=['GET'])
def trace_asset(asset_id):
    """자산 추적"""
    history = blockchain.trace_asset(asset_id)

    result = []
    for height, block_hash, tx in history:
        inputs = []
        for inp in tx.inputs:
            inputs.append({
                'txid_ref': inp.txid_ref,
                'index': inp.index
            })

        outputs = []
        for out in tx.outputs:
            outputs.append({
                'asset_id': out.asset_id,
                'pubkey_hash': out.pubkey_hash,
                'portion': out.portion
            })

        result.append({
            'height': height,
            'block_hash': block_hash,
            'txid': tx.txid,
            'inputs': inputs,
            'outputs': outputs
        })

    return jsonify(result)


if __name__ == '__main__':
    # MongoDB 초기화
    print("Initializing MongoDB...")
    init_database()

    # 기존 지갑 로드
    print("Loading wallets from database...")
    load_wallets_from_db()

    # 제네시스 블록 초기화 (DB에 없는 경우에만)
    if block_db.count_blocks() == 0:
        print("Creating genesis block...")
        msg = initialize_genesis()
        print(msg)
    else:
        print(f"Blockchain loaded from database: {block_db.count_blocks()} blocks")

    print("\n" + "=" * 60)
    print("DaBlockChain Web Application")
    print("=" * 60)
    print(f"Wallets loaded: {list(wallets.keys())}")
    print(f"Blockchain height: {blockchain.tip.header.height if blockchain.tip else 0}")
    print("\nAccess the application at: http://localhost:5001")
    print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5001)
