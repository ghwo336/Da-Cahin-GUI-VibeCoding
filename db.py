"""
MongoDB 데이터베이스 연결 및 관리 모듈
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from typing import Optional, Dict, List, Any
import os

# MongoDB 연결 설정
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "dablockchain"

# 전역 클라이언트
_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    """MongoDB 클라이언트 가져오기 (싱글톤)"""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db():
    """데이터베이스 인스턴스 가져오기"""
    client = get_client()
    return client[DB_NAME]


def init_database():
    """데이터베이스 초기화 (인덱스 생성)"""
    db = get_db()

    # Blocks 컬렉션 인덱스
    blocks_collection = db["blocks"]
    blocks_collection.create_index([("hash", ASCENDING)], unique=True)
    blocks_collection.create_index([("height", DESCENDING)])
    blocks_collection.create_index([("prev_hash", ASCENDING)])

    # Wallets 컬렉션 인덱스
    wallets_collection = db["wallets"]
    wallets_collection.create_index([("name", ASCENDING)], unique=True)
    wallets_collection.create_index([("pubkey_hash", ASCENDING)])

    # UTXO 컬렉션 인덱스
    utxo_collection = db["utxo"]
    utxo_collection.create_index([("txid", ASCENDING), ("index", ASCENDING)], unique=True)
    utxo_collection.create_index([("pubkey_hash", ASCENDING)])
    utxo_collection.create_index([("asset_id", ASCENDING)])

    print("Database initialized with indexes")


class BlockDB:
    """블록 데이터베이스 관리"""

    def __init__(self):
        self.collection = get_db()["blocks"]

    def insert_block(self, block_hash: str, block_data: Dict[str, Any]) -> bool:
        """블록 저장"""
        try:
            doc = {
                "hash": block_hash,
                "height": block_data["height"],
                "prev_hash": block_data["prev_hash"],
                "merkle_root": block_data["merkle_root"],
                "nonce": block_data["nonce"],
                "timestamp": block_data.get("timestamp"),
                "txs": block_data["txs"]
            }
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"Error inserting block: {e}")
            return False

    def get_block_by_hash(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """해시로 블록 조회"""
        return self.collection.find_one({"hash": block_hash})

    def get_block_by_height(self, height: int) -> Optional[Dict[str, Any]]:
        """높이로 블록 조회"""
        return self.collection.find_one({"height": height})

    def get_tip_block(self) -> Optional[Dict[str, Any]]:
        """최신 블록 조회"""
        return self.collection.find_one(sort=[("height", DESCENDING)])

    def get_all_blocks(self) -> List[Dict[str, Any]]:
        """모든 블록 조회 (높이 오름차순)"""
        return list(self.collection.find().sort("height", ASCENDING))

    def count_blocks(self) -> int:
        """블록 개수"""
        return self.collection.count_documents({})

    def delete_all_blocks(self):
        """모든 블록 삭제 (테스트용)"""
        self.collection.delete_many({})


class WalletDB:
    """지갑 데이터베이스 관리"""

    def __init__(self):
        self.collection = get_db()["wallets"]

    def insert_wallet(self, name: str, wallet_data: Dict[str, Any]) -> bool:
        """지갑 저장"""
        try:
            doc = {
                "name": name,
                "privkey": wallet_data["privkey"],
                "pubkey": wallet_data["pubkey"],
                "pubkey_hash": wallet_data["pubkey_hash"]
            }
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"Error inserting wallet: {e}")
            return False

    def get_wallet_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """이름으로 지갑 조회"""
        return self.collection.find_one({"name": name})

    def get_all_wallets(self) -> List[Dict[str, Any]]:
        """모든 지갑 조회"""
        return list(self.collection.find())

    def wallet_exists(self, name: str) -> bool:
        """지갑 존재 여부"""
        return self.collection.count_documents({"name": name}) > 0

    def delete_wallet(self, name: str) -> bool:
        """지갑 삭제"""
        result = self.collection.delete_one({"name": name})
        return result.deleted_count > 0

    def delete_all_wallets(self):
        """모든 지갑 삭제 (테스트용)"""
        self.collection.delete_many({})


class UTXODB:
    """UTXO 데이터베이스 관리"""

    def __init__(self):
        self.collection = get_db()["utxo"]

    def insert_utxo(self, txid: str, index: int, utxo_data: Dict[str, Any]) -> bool:
        """UTXO 저장"""
        try:
            doc = {
                "txid": txid,
                "index": index,
                "asset_id": utxo_data["asset_id"],
                "pubkey_hash": utxo_data["pubkey_hash"],
                "portion": utxo_data["portion"]
            }
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"Error inserting UTXO: {e}")
            return False

    def get_utxo(self, txid: str, index: int) -> Optional[Dict[str, Any]]:
        """UTXO 조회"""
        return self.collection.find_one({"txid": txid, "index": index})

    def get_utxos_by_pubkey_hash(self, pubkey_hash: str) -> List[Dict[str, Any]]:
        """공개키 해시로 UTXO 조회"""
        return list(self.collection.find({"pubkey_hash": pubkey_hash}))

    def get_utxos_by_asset(self, asset_id: str) -> List[Dict[str, Any]]:
        """자산 ID로 UTXO 조회"""
        return list(self.collection.find({"asset_id": asset_id}))

    def get_all_utxos(self) -> List[Dict[str, Any]]:
        """모든 UTXO 조회"""
        return list(self.collection.find())

    def delete_utxo(self, txid: str, index: int) -> bool:
        """UTXO 삭제"""
        result = self.collection.delete_one({"txid": txid, "index": index})
        return result.deleted_count > 0

    def delete_all_utxos(self):
        """모든 UTXO 삭제 (테스트용)"""
        self.collection.delete_many({})


# 전역 인스턴스
block_db = BlockDB()
wallet_db = WalletDB()
utxo_db = UTXODB()
