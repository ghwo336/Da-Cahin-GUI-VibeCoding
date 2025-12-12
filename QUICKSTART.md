# DaBlockChain - Quick Start Guide

## 5분 안에 시작하기 🚀

### 1단계: 필수 프로그램 설치

#### Python (이미 설치되어 있을 가능성 높음)
```bash
python3 --version
```

#### MongoDB 설치

**macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Windows:**
1. https://www.mongodb.com/try/download/community 접속
2. Windows 버전 다운로드 및 설치
3. 서비스로 실행

### 2단계: 프로젝트 설치

```bash
# 저장소 클론 (또는 다운로드)
git clone https://github.com/yourusername/DaBlockChain.git
cd DaBlockChain

# Python 패키지 설치
pip3 install -r requirements.txt
```

### 3단계: 실행!

```bash
python3 web_app.py
```

브라우저에서 접속: **http://localhost:5001**

## 처음 사용하는 법

### 1. 지갑 확인하기
- **Wallets** 탭으로 이동
- 이미 5개의 Genesis 지갑이 생성되어 있습니다
- 각 지갑은 하나의 자산을 100% 소유

### 2. 블록체인 보기 (3D!)
- **Chain Visualizer** 탭 클릭
- 분홍색 큐브 = Genesis Block
- 마우스로 드래그해서 둘러보기
- 블록을 클릭하면 상세 정보 표시

### 3. 첫 번째 트랜잭션 만들기
1. **Wallets** 탭에서 `genesis-wallet-0` 선택
2. **Transactions** 탭으로 이동
3. 다음 정보 입력:
   - **To**: 다른 지갑의 pubkey_hash (Wallets 탭에서 복사)
   - **Asset ID**: `asset-0`
   - **Portion**: `50` (50% 전송)
4. "Create Transaction" 클릭

### 4. 블록 채굴하기
1. **Mining** 탭으로 이동
2. "Start Mining" 클릭
3. 채굴 로그 확인
4. 완료 후 Chain Visualizer에서 새 블록 확인!

### 5. 자산 추적하기
1. **Asset Trace** 탭으로 이동
2. Asset ID 입력: `asset-0`
3. "Trace Asset" 클릭
4. 모든 거래 내역 확인

## 문제 해결

### "MongoDB connection failed"
```bash
# MongoDB가 실행 중인지 확인
mongosh

# 안 되면 MongoDB 재시작
brew services restart mongodb-community  # macOS
sudo systemctl restart mongodb           # Linux
```

### "Port 5001 already in use"
```bash
# 5001번 포트 사용 중인 프로세스 종료
lsof -ti:5001 | xargs kill -9

# 또는 web_app.py 마지막 줄을 수정하여 다른 포트 사용
app.run(debug=True, host='0.0.0.0', port=5002)
```

### "pip install failed"
```bash
# pip 업그레이드
python3 -m pip install --upgrade pip

# 패키지 하나씩 설치
pip3 install flask
pip3 install ecdsa
pip3 install pymongo
```

## 다음 단계

- 📖 자세한 내용: [README.md](README.md)
- 💾 MongoDB 설정: [MONGODB_SETUP.md](MONGODB_SETUP.md)
- 🌐 배포하기: Railway 또는 Render 사용 (README 참조)

## 즐겁게 사용하세요! 🎉
