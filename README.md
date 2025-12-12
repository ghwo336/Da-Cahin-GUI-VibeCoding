# daChain - 간소화된 블록체인 구현

UTXO 기반의 교육용 블록체인 프로젝트입니다.

## 🌐 웹 인터페이스 (권장)

웹 브라우저에서 블록체인을 시각화하고 관리할 수 있습니다!

### 실행 방법

```bash
# 의존성 설치
pip3 install flask ecdsa

# 웹 애플리케이션 실행
python3 web_app.py
```

웹 브라우저에서 접속: **http://localhost:5001**

### 주요 기능

- 💼 **지갑 관리**: 지갑 생성, 선택, 잔액 확인
- ⛓️ **블록체인 탐색**: 전체 블록체인 조회, 블록 상세 정보
- 💸 **트랜잭션**: 자산 전송 트랜잭션 생성 및 관리
- ⛏️ **채굴**: 실시간 블록 채굴 및 로그 확인
- 🔍 **자산 추적**: 특정 자산의 거래 내역 추적

---

## 프로젝트 구조

```
DaBlockCahin/
├── crypto.py          # 암호화 및 해시 유틸리티
├── models.py          # 데이터 구조 (Transaction, Block 등)
├── utxo.py            # UTXO 집합 관리
├── wallet.py          # 지갑 (키 관리, 서명/검증)
├── utils.py           # 유틸리티 함수 (머클 트리, 제네시스 블록 등)
├── blockchain.py      # 블록체인 핵심 로직 (검증, 채굴, 추적)
├── node.py            # 풀 노드 (P2P 네트워크 시뮬레이션)
├── processes.py       # 유저/마스터 프로세스
├── cli.py             # CLI 인터페이스
└── main.py            # 메인 진입점
```

## 모듈 설명

### crypto.py

- SHA-256 해시 함수
- ECDSA 서명 라이브러리 임포트

### models.py

- `TxInput`: 트랜잭션 입력
- `TxOutput`: 트랜잭션 출력
- `Transaction`: 트랜잭션 (입력, 출력, ID, 서명)
- `BlockHeader`: 블록 헤더 (높이, 이전 해시, 머클 루트, nonce)
- `Block`: 블록 (헤더 + 트랜잭션 목록)

### utxo.py

- `UTXOSet`: 미사용 출력(UTXO) 집합 관리

### wallet.py

- `Wallet`: ECDSA 키 쌍 관리, 서명/검증

### utils.py

- `merkle_root()`: 머클 루트 계산
- `create_genesis()`: 제네시스 블록 생성
- `create_random_valid_tx()`: 유효한 랜덤 트랜잭션 생성
- `create_random_invalid_tx()`: 무효한 랜덤 트랜잭션 생성 (테스트용)

### blockchain.py

- `Blockchain`: 블록체인 핵심 클래스
  - 트랜잭션 검증
  - 블록 채굴 (PoW)
  - 자산 추적
  - 체인 구축

### node.py

- `FullNode`: 풀 노드 구현
  - 트랜잭션 수신/전파
  - 멤풀 관리
  - 블록 채굴/수신

### processes.py

- `UserProcess`: 랜덤 트랜잭션 생성 스레드
- `MasterProcess`: 네트워크 관리 및 모니터링

### cli.py

- `DaChainCLI`: CLI 인터페이스
  - 명령어 파싱 및 실행

### main.py

- 프로그램 진입점

## CLI 버전 실행

터미널에서 명령어로 블록체인을 관리하는 방식입니다.

### 설치

```bash
pip install ecdsa
```

### 실행

```bash
python3 main.py
```

## 사용 예시

```
> initiate daChain 8
> initiate fullNodes 5
> run userProcess
> mine F0
> verify-transaction F0
> snapshot daChain ALL
> trace asset-0 ALL
> stop userProcess
> exit
```

## 주요 기능

1. **UTXO 기반 트랜잭션**: 비트코인과 유사한 UTXO 모델
2. **PoW 채굴**: SHA-256 기반 작업 증명
3. **트랜잭션 검증**: 서명, 잔고, 자산 ID 검증
4. **자산 추적**: 특정 자산의 거래 내역 추적
5. **P2P 네트워크 시뮬레이션**: 노드 간 트랜잭션/블록 전파

## 라이선스

MIT
