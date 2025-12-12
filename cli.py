"""
CLI 인터페이스 모듈
"""
import random
from typing import List, Optional

from blockchain import Blockchain
from wallet import Wallet
from node import FullNode
from processes import UserProcess, MasterProcess
from utils import create_genesis


class DaChainCLI:
    """
    daChain CLI 인터페이스
    사용자 명령 처리 및 시스템 관리
    """

    def __init__(self):
        self.blockchain: Optional[Blockchain] = None
        self.wallets: List[Wallet] = []
        self.nodes: List[FullNode] = []
        self.user_proc: Optional[UserProcess] = None
        self.master: Optional[MasterProcess] = None

    def print_help(self):
        """도움말 출력"""
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

    def initiate_dachain(self, n: int):
        """daChain 초기화"""
        if self.blockchain is not None:
            print("이미 daChain 이 초기화되어 있습니다.")
            return

        self.blockchain = Blockchain()
        # 초기 소유자 N개 + 추가 참여자 N개 = 총 2N개 지갑
        self.wallets = [Wallet() for _ in range(2 * n)]

        genesis = create_genesis(num_assets=n, initial_wallets=self.wallets[:n])
        self.blockchain.add_genesis_block(genesis)

        print(f"[genesis] created with {n} assets")
        print(f"지갑 총 {len(self.wallets)}개 생성 (초기 소유자 {n}, 추가 참여자 {n})")

    def initiate_fullnodes(self, l: int):
        """풀 노드 초기화"""
        if self.blockchain is None:
            print("먼저 initiate daChain N 을 실행하세요.")
            return

        if self.nodes:
            print("이미 fullNodes 가 초기화되어 있습니다.")
            return

        self.nodes = []
        self.master = MasterProcess(self.nodes, self.blockchain)

        for i in range(l):
            node = FullNode(f"F{i}", self.blockchain, master=self.master)
            self.nodes.append(node)

        # 풀 메시 네트워크로 연결
        for i in range(l):
            for j in range(i + 1, l):
                self.nodes[i].connect_peer(self.nodes[j])
                self.nodes[j].connect_peer(self.nodes[i])

        print(f"{l} 개의 full node 생성 및 상호 연결 완료.")

    def run_userprocess(self):
        """유저 프로세스 시작"""
        if self.blockchain is None or not self.nodes or not self.wallets:
            print("먼저 daChain 과 fullNodes 를 초기화하세요.")
            return

        if self.user_proc is not None and self.user_proc.running:
            print("userProcess 가 이미 실행 중입니다.")
            return

        self.user_proc = UserProcess(
            nodes=self.nodes,
            blockchain=self.blockchain,
            wallets=self.wallets,
            invalid_ratio=0.2,
            interval=0.5
        )
        self.user_proc.start()

    def stop_userprocess(self):
        """유저 프로세스 중지"""
        if self.user_proc is None or not self.user_proc.running:
            print("userProcess 가 실행 중이 아닙니다.")
            return
        self.user_proc.stop()

    def mine(self, node_id: str):
        """특정 노드에서 블록 채굴"""
        node = None
        for n in self.nodes:
            if n.node_id == node_id:
                node = n
                break

        if node is None:
            print(f"no such node {node_id}")
            return

        node.mine()

    def verify_transaction(self, node_id: str):
        """트랜잭션 검증"""
        if self.master is None:
            print("masterProcess 가 아직 없습니다. 먼저 fullNodes 를 초기화하세요.")
            return
        self.master.verify_transaction(node_id)

    def snapshot_dachain(self, target: str):
        """체인 스냅샷"""
        if self.master is None:
            print("masterProcess 가 아직 없습니다.")
            return

        if target == "ALL":
            self.master.snapshot_daChain()
        else:
            self.master.snapshot_daChain(target)

    def trace_asset(self, asset_id: str, limit_str: str):
        """자산 추적"""
        if self.master is None:
            print("masterProcess 가 아직 없습니다.")
            return

        if limit_str == "ALL":
            self.master.trace_asset(asset_id, limit=None)
        else:
            try:
                k = int(limit_str)
                self.master.trace_asset(asset_id, limit=k)
            except ValueError:
                print("k 는 정수이거나 ALL 이어야 합니다.")

    def run(self):
        """CLI 메인 루프"""
        random.seed(0)
        self.print_help()

        while True:
            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not cmd:
                continue

            if cmd == "exit":
                if self.user_proc is not None:
                    self.user_proc.stop()
                break

            parts = cmd.split()

            # initiate daChain N
            if parts[0] == "initiate" and len(parts) >= 3 and parts[1] == "daChain":
                try:
                    n = int(parts[2])
                    self.initiate_dachain(n)
                except ValueError:
                    print("N 은 정수여야 합니다.")

            # initiate fullNodes L
            elif parts[0] == "initiate" and len(parts) >= 3 and parts[1] == "fullNodes":
                try:
                    l = int(parts[2])
                    self.initiate_fullnodes(l)
                except ValueError:
                    print("L 은 정수여야 합니다.")

            # run userProcess
            elif parts[0] == "run" and len(parts) >= 2 and parts[1] == "userProcess":
                self.run_userprocess()

            # stop userProcess
            elif parts[0] == "stop" and len(parts) >= 2 and parts[1] == "userProcess":
                self.stop_userprocess()

            # mine F0
            elif parts[0] == "mine" and len(parts) == 2:
                self.mine(parts[1])

            # verify-transaction F0
            elif parts[0] == "verify-transaction" and len(parts) == 2:
                self.verify_transaction(parts[1])

            # snapshot daChain ALL/F0
            elif parts[0] == "snapshot" and len(parts) >= 3 and parts[1] == "daChain":
                self.snapshot_dachain(parts[2])

            # trace asset-0 ALL/5
            elif parts[0] == "trace" and len(parts) >= 2:
                asset_id = parts[1]
                limit_str = parts[2] if len(parts) == 3 else "ALL"
                self.trace_asset(asset_id, limit_str)

            else:
                print("알 수 없는 명령입니다.")
