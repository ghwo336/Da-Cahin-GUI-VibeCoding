# MongoDB 설정 가이드

## 개요
DaBlockChain은 이제 MongoDB를 사용하여 블록체인 데이터를 영구 저장합니다.

## MongoDB 설치 (macOS)

```bash
# Homebrew를 사용한 MongoDB 설치
brew tap mongodb/brew
brew install mongodb-community

# MongoDB 시작
brew services start mongodb-community

# MongoDB 상태 확인
brew services list | grep mongodb
```

## MongoDB 연결 설정

### 기본 설정
기본적으로 `mongodb://localhost:27017/`에 연결됩니다.

### 환경 변수 설정 (선택사항)
다른 MongoDB 서버를 사용하려면 환경 변수를 설정하세요:

```bash
export MONGO_URI="mongodb://username:password@host:port/"
```

## 데이터베이스 구조

### 데이터베이스 이름
`dablockchain`

### 컬렉션

#### 1. blocks
블록체인의 모든 블록을 저장합니다.

**필드:**
- `hash` (string, unique): 블록 해시
- `height` (int, indexed): 블록 높이
- `prev_hash` (string, indexed): 이전 블록 해시
- `merkle_root` (string): 머클 루트
- `nonce` (int): PoW nonce
- `timestamp` (int): 생성 시간 (Unix timestamp)
- `txs` (array): 트랜잭션 목록

**인덱스:**
- `hash`: unique index
- `height`: descending index
- `prev_hash`: ascending index

#### 2. wallets
사용자 지갑 정보를 저장합니다.

**필드:**
- `name` (string, unique): 지갑 이름
- `privkey` (string): 개인키 (hex)
- `pubkey` (string): 공개키 (hex)
- `pubkey_hash` (string, indexed): 공개키 해시

**인덱스:**
- `name`: unique index
- `pubkey_hash`: ascending index

#### 3. utxo
미사용 트랜잭션 출력(UTXO)을 저장합니다.

**필드:**
- `txid` (string): 트랜잭션 ID
- `index` (int): 출력 인덱스
- `asset_id` (string, indexed): 자산 ID
- `pubkey_hash` (string, indexed): 소유자 공개키 해시
- `portion` (int): 지분 (0-100)

**인덱스:**
- `(txid, index)`: unique compound index
- `pubkey_hash`: ascending index
- `asset_id`: ascending index

## 데이터베이스 관리

### MongoDB 셸 접속
```bash
mongosh
```

### 데이터베이스 선택
```javascript
use dablockchain
```

### 컬렉션 확인
```javascript
show collections
```

### 블록 조회
```javascript
// 모든 블록 조회
db.blocks.find().pretty()

// 최신 블록 조회
db.blocks.find().sort({height: -1}).limit(1).pretty()

// 특정 높이의 블록 조회
db.blocks.find({height: 0}).pretty()
```

### 지갑 조회
```javascript
// 모든 지갑 조회
db.wallets.find().pretty()

// 특정 지갑 조회
db.wallets.find({name: "genesis-wallet-0"}).pretty()
```

### UTXO 조회
```javascript
// 모든 UTXO 조회
db.utxo.find().pretty()

// 특정 지갑의 UTXO 조회
db.utxo.find({pubkey_hash: "YOUR_PUBKEY_HASH"}).pretty()

// 특정 자산의 UTXO 조회
db.utxo.find({asset_id: "ASSET_ID"}).pretty()
```

### 데이터베이스 초기화 (주의!)
```javascript
// 모든 데이터 삭제
db.blocks.deleteMany({})
db.wallets.deleteMany({})
db.utxo.deleteMany({})
```

## 백업 및 복원

### 백업
```bash
mongodump --db dablockchain --out /path/to/backup
```

### 복원
```bash
mongorestore --db dablockchain /path/to/backup/dablockchain
```

## 주요 기능

### 자동 로딩
웹 애플리케이션 시작 시 자동으로:
1. MongoDB에 연결
2. 인덱스 생성
3. 기존 블록체인 데이터 로드
4. 기존 지갑 로드
5. UTXO 집합 재구성

### 실시간 동기화
모든 작업이 메모리와 MongoDB에 동시에 저장됩니다:
- 블록 채굴: 블록 + UTXO 업데이트
- 지갑 생성: 지갑 정보 저장
- 트랜잭션 적용: UTXO 추가/제거

## 문제 해결

### MongoDB 연결 실패
```bash
# MongoDB 상태 확인
brew services list | grep mongodb

# MongoDB 재시작
brew services restart mongodb-community

# MongoDB 로그 확인
tail -f /opt/homebrew/var/log/mongodb/mongo.log
```

### 데이터베이스 권한 문제
MongoDB가 localhost에서 실행 중이면 기본적으로 인증이 필요 없습니다.
원격 서버를 사용하는 경우 MONGO_URI에 인증 정보를 포함하세요.

## 성능 최적화

### 인덱스 확인
```javascript
db.blocks.getIndexes()
db.wallets.getIndexes()
db.utxo.getIndexes()
```

### 쿼리 성능 분석
```javascript
db.blocks.find({height: 5}).explain("executionStats")
```

## 보안 권장사항

1. **프로덕션 환경**: 반드시 MongoDB 인증 활성화
2. **방화벽 설정**: MongoDB 포트(27017)를 외부에서 접근 불가하도록 설정
3. **백업**: 정기적인 데이터베이스 백업 수행
4. **암호화**: 민감한 데이터(개인키)는 추가 암호화 고려
