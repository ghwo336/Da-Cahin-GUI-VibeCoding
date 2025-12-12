# DaBlockChain - Web-Based Blockchain Visualizer

UTXO 기반의 블록체인 구현과 3D 시각화를 제공하는 웹 애플리케이션입니다.

## 📖 프로젝트 배경

이 프로젝트는 블록체인 강의를 수강하며 학습한 내용을 바탕으로 **100% Claude AI와의 바이브 코딩**으로 완성했습니다. 강의에서 배운 UTXO 모델, PoW 채굴, 머클 트리 등의 핵심 개념을 Claude와 대화하며 구현하고, 웹 GUI부터 3D 시각화, MongoDB 통합까지 모든 코드를 AI 페어 프로그래밍으로 작성했습니다.

### 개발 과정 (100% AI 바이브 코딩)
- 🎓 **블록체인 이론 학습**: 강의에서 배운 UTXO, PoW, 전자서명 개념
- 💬 **Claude와 대화**: 개념을 설명하고 구현 방향 논의
- 🤖 **AI 페어 프로그래밍**: 모든 코드를 Claude가 작성 (Python, JavaScript, HTML/CSS)
- 🎨 **3D 시각화**: "3D로 만들어줘" → Claude가 Three.js 구현
- 💾 **MongoDB 통합**: "데이터베이스에 저장하고싶어" → Claude가 MongoDB 설계 및 통합
- 🎯 **완성**: CLI부터 웹 GUI까지 100% 바이브 코딩으로 구현

## ✨ 주요 기능

- 🎮 **3D 블록체인 시각화**: Three.js를 사용한 인터랙티브 3D 블록 렌더링
- 💼 **지갑 관리**: 지갑 생성, 선택, 잔액 확인
- ⛓️ **블록체인 탐색**: 전체 블록체인 조회, 블록 상세 정보
- 💸 **트랜잭션**: 자산 전송 트랜잭션 생성 및 관리
- ⛏️ **채굴**: 실시간 블록 채굴 (PoW) 및 로그 확인
- 🔍 **자산 추적**: 특정 자산의 전체 거래 내역 추적
- 💾 **MongoDB 영구 저장**: 블록체인 데이터를 MongoDB에 저장

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip3 install -r requirements.txt
```

**requirements.txt:**
```
flask==3.0.0
ecdsa==0.18.0
pymongo==4.6.1
```

### 2. MongoDB 설치 및 실행

**macOS (Homebrew):**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mongodb
sudo systemctl start mongodb
```

**Windows:**
MongoDB 공식 사이트에서 설치: https://www.mongodb.com/try/download/community

### 3. 웹 애플리케이션 실행

```bash
python3 web_app.py
```

### 4. 브라우저 접속

**http://localhost:5001**

첫 실행 시 자동으로:
- Genesis 블록 생성
- 5개의 초기 지갑 생성
- MongoDB 인덱스 설정

## 📁 프로젝트 구조

```
DaBlockCahin/
├── web_app.py           # Flask 웹 애플리케이션 (메인 진입점)
├── blockchain.py        # 블록체인 핵심 로직 (검증, 채굴, MongoDB 연동)
├── db.py                # MongoDB 데이터베이스 관리
├── models.py            # 데이터 구조 (Transaction, Block 등)
├── wallet.py            # 지갑 (ECDSA 키 관리, 서명/검증)
├── utxo.py              # UTXO 집합 관리
├── utils.py             # 유틸리티 (머클 트리, 제네시스 블록)
├── crypto.py            # 암호화 및 해시
├── templates/           # HTML 템플릿
│   └── index.html
├── static/              # 정적 파일
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js
│       └── visualizer3d.js
├── requirements.txt     # Python 의존성
└── MONGODB_SETUP.md     # MongoDB 설정 가이드
```

## 🎮 웹 인터페이스 사용법

### 지갑 관리
1. **Wallets** 탭에서 지갑 생성
2. 지갑을 클릭하여 선택
3. 잔액 확인

### 3D 블록체인 시각화
1. **Chain Visualizer** 탭 클릭
2. 3D로 렌더링된 블록 확인
3. 마우스로 좌우 드래그하여 뷰 이동
4. 블록 클릭 시 상세 정보 모달 표시

### 트랜잭션 생성
1. **Transactions** 탭에서 지갑 선택
2. 수신자 공개키 해시, 자산 ID, 비율 입력
3. "Create Transaction" 클릭
4. 펜딩 트랜잭션 목록에서 확인

### 블록 채굴
1. **Mining** 탭에서 "Start Mining" 클릭
2. 실시간 채굴 로그 확인
3. 채굴 완료 후 Chain Visualizer에서 새 블록 확인

### 자산 추적
1. **Asset Trace** 탭에서 자산 ID 입력
2. 해당 자산의 모든 거래 내역 확인

## 🛠️ 기술 스택

### Backend
- **Flask**: Python 웹 프레임워크
- **MongoDB**: NoSQL 데이터베이스
- **PyMongo**: MongoDB Python 드라이버
- **ECDSA**: 전자 서명

### Frontend
- **Three.js**: 3D 그래픽 렌더링
- **Vanilla JavaScript**: 프론트엔드 로직
- **CSS3**: 스타일링 및 애니메이션

### 블록체인
- **UTXO 모델**: 비트코인과 유사한 UTXO 기반 트랜잭션
- **SHA-256**: 해시 함수
- **PoW (Proof of Work)**: 작업 증명 기반 채굴
- **Merkle Tree**: 트랜잭션 검증

## 📊 MongoDB 컬렉션

### blocks
블록체인의 모든 블록
- `hash` (unique): 블록 해시
- `height`: 블록 높이
- `prev_hash`: 이전 블록 해시
- `merkle_root`: 머클 루트
- `nonce`: PoW nonce
- `timestamp`: 생성 시간
- `txs`: 트랜잭션 배열

### wallets
사용자 지갑 정보
- `name` (unique): 지갑 이름
- `privkey`: 개인키 (hex)
- `pubkey`: 공개키 (hex)
- `pubkey_hash`: 공개키 해시

### utxo
미사용 트랜잭션 출력
- `txid`, `index` (unique): UTXO 식별자
- `asset_id`: 자산 ID
- `pubkey_hash`: 소유자 공개키 해시
- `portion`: 지분 (0-100)

## 🔧 개발 및 디버깅

### MongoDB 데이터 확인
```bash
mongosh dablockchain

# 블록 조회
db.blocks.find().pretty()

# 지갑 조회
db.wallets.find().pretty()

# UTXO 조회
db.utxo.find().pretty()
```

### 데이터베이스 초기화
```bash
mongosh dablockchain
db.blocks.deleteMany({})
db.wallets.deleteMany({})
db.utxo.deleteMany({})
```

### 로그 확인
웹 애플리케이션 실행 시 터미널에서 로그 확인:
- Genesis 블록 생성
- 블록체인 로드
- 채굴 진행 상황

## 🌐 배포 옵션

### Railway (권장)
1. Railway 계정 생성: https://railway.app
2. GitHub 저장소 연결
3. MongoDB Atlas 추가
4. 환경 변수 설정: `MONGO_URI`
5. 자동 배포

### Render
1. Render 계정 생성: https://render.com
2. Web Service 생성
3. MongoDB Atlas 연결
4. 환경 변수 설정
5. 배포

자세한 배포 가이드는 별도 문서 참조.

## 📚 주요 개념

### UTXO (Unspent Transaction Output)
- 비트코인과 동일한 UTXO 기반 트랜잭션 모델
- 각 트랜잭션은 이전 UTXO를 소비하고 새 UTXO 생성
- 잔액 = 소유한 모든 UTXO의 합

### Proof of Work (PoW)
- SHA-256 해시 기반 작업 증명
- 목표값보다 작은 해시를 찾을 때까지 nonce 증가
- 난이도: `00000f...` (앞 5자리가 0)

### Merkle Tree
- 트랜잭션들의 해시를 트리 구조로 결합
- 블록 헤더에 루트 해시만 저장
- 효율적인 트랜잭션 검증

## 🔒 보안 고려사항

1. **개인키 보호**: MongoDB에 개인키가 평문으로 저장됨 (프로덕션에서는 암호화 필요)
2. **네트워크 보안**: 현재는 로컬호스트만 지원 (프로덕션에서는 HTTPS 필요)
3. **인증**: 현재 인증 없음 (프로덕션에서는 사용자 인증 추가 필요)

## 📝 라이선스

MIT License

## 🤝 기여

이슈 및 풀 리퀘스트 환영합니다!

## 📞 문의

GitHub Issues를 통해 문의해주세요.
