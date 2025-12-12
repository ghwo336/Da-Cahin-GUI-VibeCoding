"""
DaBlockChain GUI Application
tkinter 기반 블록체인 그래픽 인터페이스
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from typing import Optional, List, Dict

from blockchain import Blockchain
from wallet import Wallet
from models import Transaction, TxInput, TxOutput
from utils import create_genesis
from crypto import sha256_hex


class BlockchainGUI:
    """블록체인 GUI 애플리케이션"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DaBlockChain - GUI")
        self.root.geometry("1200x800")

        # 블록체인 및 지갑 초기화
        self.blockchain = Blockchain()
        self.wallets: Dict[str, Wallet] = {}
        self.pending_txs: List[Transaction] = []
        self.current_wallet: Optional[str] = None

        # UI 구성
        self.setup_ui()

    def setup_ui(self):
        """UI 구성"""
        # 메뉴바
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 노트북 (탭)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # 탭 생성
        self.create_wallet_tab()
        self.create_blockchain_tab()
        self.create_transaction_tab()
        self.create_mining_tab()
        self.create_asset_tab()

        # 상태바
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                            bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_wallet_tab(self):
        """지갑 관리 탭"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💼 Wallet")

        # 상단: 지갑 생성
        top_frame = ttk.LabelFrame(frame, text="Wallet Management", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text="Wallet Name:").grid(row=0, column=0, sticky='w', padx=5)
        self.wallet_name_entry = ttk.Entry(top_frame, width=30)
        self.wallet_name_entry.grid(row=0, column=1, padx=5)

        ttk.Button(top_frame, text="Create Wallet",
                  command=self.create_wallet).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="Refresh List",
                  command=self.refresh_wallet_list).grid(row=0, column=3, padx=5)

        # 중간: 지갑 목록
        middle_frame = ttk.LabelFrame(frame, text="Wallet List", padding=10)
        middle_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # 트리뷰
        columns = ('name', 'address', 'selected')
        self.wallet_tree = ttk.Treeview(middle_frame, columns=columns, show='headings', height=10)
        self.wallet_tree.heading('name', text='Name')
        self.wallet_tree.heading('address', text='Public Key Hash')
        self.wallet_tree.heading('selected', text='Selected')

        self.wallet_tree.column('name', width=150)
        self.wallet_tree.column('address', width=400)
        self.wallet_tree.column('selected', width=80)

        scrollbar = ttk.Scrollbar(middle_frame, orient='vertical', command=self.wallet_tree.yview)
        self.wallet_tree.configure(yscrollcommand=scrollbar.set)

        self.wallet_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 하단: 지갑 선택 및 잔액 확인
        bottom_frame = ttk.LabelFrame(frame, text="Wallet Actions", padding=10)
        bottom_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(bottom_frame, text="Select Wallet",
                  command=self.select_wallet).grid(row=0, column=0, padx=5)
        ttk.Button(bottom_frame, text="Check Balance",
                  command=self.check_balance).grid(row=0, column=1, padx=5)

        self.balance_text = scrolledtext.ScrolledText(bottom_frame, height=8, width=100)
        self.balance_text.grid(row=1, column=0, columnspan=4, pady=5)

    def create_blockchain_tab(self):
        """블록체인 뷰어 탭"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⛓️ Blockchain")

        # 상단: 컨트롤
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(top_frame, text="Refresh Blockchain",
                  command=self.refresh_blockchain).pack(side='left', padx=5)
        ttk.Button(top_frame, text="View Block Details",
                  command=self.view_block_details).pack(side='left', padx=5)

        # 중간: 블록 목록
        middle_frame = ttk.LabelFrame(frame, text="Block List", padding=10)
        middle_frame.pack(fill='both', expand=True, padx=10, pady=5)

        columns = ('height', 'hash', 'prev_hash', 'txs', 'nonce')
        self.block_tree = ttk.Treeview(middle_frame, columns=columns, show='headings', height=15)
        self.block_tree.heading('height', text='Height')
        self.block_tree.heading('hash', text='Block Hash')
        self.block_tree.heading('prev_hash', text='Previous Hash')
        self.block_tree.heading('txs', text='Transactions')
        self.block_tree.heading('nonce', text='Nonce')

        self.block_tree.column('height', width=60)
        self.block_tree.column('hash', width=200)
        self.block_tree.column('prev_hash', width=200)
        self.block_tree.column('txs', width=100)
        self.block_tree.column('nonce', width=100)

        scrollbar = ttk.Scrollbar(middle_frame, orient='vertical', command=self.block_tree.yview)
        self.block_tree.configure(yscrollcommand=scrollbar.set)

        self.block_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 하단: 블록 상세 정보
        bottom_frame = ttk.LabelFrame(frame, text="Block Details", padding=10)
        bottom_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.block_detail_text = scrolledtext.ScrolledText(bottom_frame, height=10)
        self.block_detail_text.pack(fill='both', expand=True)

    def create_transaction_tab(self):
        """트랜잭션 생성 탭"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💸 Transaction")

        # 상단: 트랜잭션 생성 폼
        top_frame = ttk.LabelFrame(frame, text="Create Transaction", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text="From (Current Wallet):").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.tx_from_label = ttk.Label(top_frame, text="No wallet selected", foreground='red')
        self.tx_from_label.grid(row=0, column=1, sticky='w', padx=5, pady=2)

        ttk.Label(top_frame, text="To (Recipient PubKey Hash):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.tx_to_entry = ttk.Entry(top_frame, width=70)
        self.tx_to_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(top_frame, text="Asset ID:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.tx_asset_entry = ttk.Entry(top_frame, width=70)
        self.tx_asset_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(top_frame, text="Portion (%):").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.tx_portion_entry = ttk.Entry(top_frame, width=20)
        self.tx_portion_entry.grid(row=3, column=1, sticky='w', padx=5, pady=2)

        ttk.Button(top_frame, text="Create & Submit Transaction",
                  command=self.create_transaction).grid(row=4, column=0, columnspan=2, pady=10)

        # 하단: 펜딩 트랜잭션 목록
        bottom_frame = ttk.LabelFrame(frame, text="Pending Transactions", padding=10)
        bottom_frame.pack(fill='both', expand=True, padx=10, pady=5)

        ttk.Button(bottom_frame, text="Refresh",
                  command=self.refresh_pending_txs).pack(anchor='w', pady=5)

        self.pending_tx_text = scrolledtext.ScrolledText(bottom_frame, height=20)
        self.pending_tx_text.pack(fill='both', expand=True)

    def create_mining_tab(self):
        """마이닝 탭"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⛏️ Mining")

        # 상단: 마이닝 컨트롤
        top_frame = ttk.LabelFrame(frame, text="Mining Control", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text="Mine a new block with pending transactions").pack(pady=5)
        ttk.Button(top_frame, text="Start Mining",
                  command=self.start_mining, width=20).pack(pady=5)

        self.mining_progress = ttk.Progressbar(top_frame, mode='indeterminate', length=400)
        self.mining_progress.pack(pady=5)

        # 중간: 마이닝 로그
        middle_frame = ttk.LabelFrame(frame, text="Mining Log", padding=10)
        middle_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.mining_log = scrolledtext.ScrolledText(middle_frame, height=25)
        self.mining_log.pack(fill='both', expand=True)

    def create_asset_tab(self):
        """자산 추적 탭"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔍 Asset Trace")

        # 상단: 자산 ID 입력
        top_frame = ttk.LabelFrame(frame, text="Asset Tracing", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text="Asset ID:").grid(row=0, column=0, sticky='w', padx=5)
        self.asset_id_entry = ttk.Entry(top_frame, width=70)
        self.asset_id_entry.grid(row=0, column=1, padx=5)

        ttk.Button(top_frame, text="Trace Asset",
                  command=self.trace_asset).grid(row=0, column=2, padx=5)

        # 하단: 자산 이력
        bottom_frame = ttk.LabelFrame(frame, text="Asset History", padding=10)
        bottom_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.asset_trace_text = scrolledtext.ScrolledText(bottom_frame, height=30)
        self.asset_trace_text.pack(fill='both', expand=True)

    # ==================== 지갑 관련 메서드 ====================

    def create_wallet(self):
        """지갑 생성"""
        name = self.wallet_name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a wallet name")
            return

        if name in self.wallets:
            messagebox.showerror("Error", f"Wallet '{name}' already exists")
            return

        self.wallets[name] = Wallet()
        messagebox.showinfo("Success", f"Wallet '{name}' created successfully")
        self.wallet_name_entry.delete(0, tk.END)
        self.refresh_wallet_list()

    def refresh_wallet_list(self):
        """지갑 목록 새로고침"""
        # 기존 항목 삭제
        for item in self.wallet_tree.get_children():
            self.wallet_tree.delete(item)

        # 지갑 추가
        for name, wallet in self.wallets.items():
            pubkey_hash = wallet.pubkey_hash
            selected = "✓" if name == self.current_wallet else ""
            self.wallet_tree.insert('', 'end', values=(name, pubkey_hash, selected))

        self.status_var.set(f"Loaded {len(self.wallets)} wallets")

    def select_wallet(self):
        """지갑 선택"""
        selection = self.wallet_tree.selection()
        if not selection:
            messagebox.showerror("Error", "Please select a wallet from the list")
            return

        item = self.wallet_tree.item(selection[0])
        wallet_name = item['values'][0]
        self.current_wallet = wallet_name
        self.tx_from_label.config(text=wallet_name, foreground='green')
        self.refresh_wallet_list()
        messagebox.showinfo("Success", f"Selected wallet: {wallet_name}")

    def check_balance(self):
        """잔액 확인"""
        if not self.current_wallet:
            messagebox.showerror("Error", "Please select a wallet first")
            return

        wallet = self.wallets[self.current_wallet]
        balances = self.get_balance(wallet)

        self.balance_text.delete(1.0, tk.END)
        self.balance_text.insert(tk.END, f"Balance for wallet: {self.current_wallet}\n")
        self.balance_text.insert(tk.END, f"Public Key Hash: {wallet.pubkey_hash}\n")
        self.balance_text.insert(tk.END, "=" * 80 + "\n\n")

        if not balances:
            self.balance_text.insert(tk.END, "No assets found\n")
        else:
            for asset_id, portion in balances.items():
                self.balance_text.insert(tk.END, f"Asset ID: {asset_id}\n")
                self.balance_text.insert(tk.END, f"Portion: {portion}%\n\n")

    def get_balance(self, wallet: Wallet) -> Dict[str, int]:
        """지갑의 잔액 계산"""
        balances: Dict[str, int] = {}
        for (txid, idx), utxo in self.blockchain.utxo.all_utxos().items():
            if utxo.pubkey_hash == wallet.pubkey_hash:
                if utxo.asset_id not in balances:
                    balances[utxo.asset_id] = 0
                balances[utxo.asset_id] += utxo.portion
        return balances

    # ==================== 블록체인 관련 메서드 ====================

    def refresh_blockchain(self):
        """블록체인 새로고침"""
        # 기존 항목 삭제
        for item in self.block_tree.get_children():
            self.block_tree.delete(item)

        # 블록 추가 (제네시스부터)
        chain = self.blockchain.build_chain_from_tip()
        chain.reverse()  # 제네시스가 먼저 오도록

        for block_hash, block in chain:
            self.block_tree.insert('', 'end', values=(
                block.header.height,
                block_hash[:32] + "...",
                block.header.prev_hash[:32] + "...",
                len(block.txs),
                block.header.nonce
            ))

        self.status_var.set(f"Blockchain: {len(chain)} blocks")

    def view_block_details(self):
        """블록 상세 보기"""
        selection = self.block_tree.selection()
        if not selection:
            messagebox.showerror("Error", "Please select a block from the list")
            return

        item = self.block_tree.item(selection[0])
        height = item['values'][0]

        # 해당 높이의 블록 찾기
        chain = self.blockchain.build_chain_from_tip()
        for block_hash, block in chain:
            if block.header.height == height:
                self.display_block_details(block_hash, block)
                return

    def display_block_details(self, block_hash: str, block):
        """블록 상세 정보 표시"""
        self.block_detail_text.delete(1.0, tk.END)
        self.block_detail_text.insert(tk.END, f"Block Hash: {block_hash}\n")
        self.block_detail_text.insert(tk.END, f"Height: {block.header.height}\n")
        self.block_detail_text.insert(tk.END, f"Previous Hash: {block.header.prev_hash}\n")
        self.block_detail_text.insert(tk.END, f"Merkle Root: {block.header.merkle_root}\n")
        self.block_detail_text.insert(tk.END, f"Nonce: {block.header.nonce}\n")
        self.block_detail_text.insert(tk.END, f"Transactions: {len(block.txs)}\n")
        self.block_detail_text.insert(tk.END, "=" * 80 + "\n\n")

        for i, tx in enumerate(block.txs):
            self.block_detail_text.insert(tk.END, f"Transaction {i+1}:\n")
            self.block_detail_text.insert(tk.END, f"  TXID: {tx.txid}\n")
            self.block_detail_text.insert(tk.END, f"  Inputs: {len(tx.inputs)}\n")
            self.block_detail_text.insert(tk.END, f"  Outputs: {len(tx.outputs)}\n")
            for j, out in enumerate(tx.outputs):
                self.block_detail_text.insert(tk.END, f"    Output {j}: Asset={out.asset_id[:16]}... Portion={out.portion}%\n")
            self.block_detail_text.insert(tk.END, "\n")

    # ==================== 트랜잭션 관련 메서드 ====================

    def create_transaction(self):
        """트랜잭션 생성"""
        if not self.current_wallet:
            messagebox.showerror("Error", "Please select a wallet first")
            return

        to_pubkey_hash = self.tx_to_entry.get().strip()
        asset_id = self.tx_asset_entry.get().strip()
        portion_str = self.tx_portion_entry.get().strip()

        if not to_pubkey_hash or not asset_id or not portion_str:
            messagebox.showerror("Error", "Please fill all fields")
            return

        try:
            portion = int(portion_str)
            if portion <= 0 or portion > 100:
                raise ValueError("Portion must be between 1 and 100")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid portion: {e}")
            return

        wallet = self.wallets[self.current_wallet]

        try:
            tx = self.create_transfer_tx(wallet, to_pubkey_hash, asset_id, portion)
            self.pending_txs.append(tx)
            messagebox.showinfo("Success", f"Transaction created successfully\nTXID: {tx.txid}")

            # 입력 필드 초기화
            self.tx_to_entry.delete(0, tk.END)
            self.tx_asset_entry.delete(0, tk.END)
            self.tx_portion_entry.delete(0, tk.END)

            self.refresh_pending_txs()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create transaction: {e}")

    def create_transfer_tx(self, wallet: Wallet, to_pubkey_hash: str, asset_id: str, portion: int) -> Transaction:
        """트랜잭션 생성"""
        # 해당 자산의 UTXO 찾기
        inputs_list = []
        total_in = 0

        for (txid, idx), utxo in self.blockchain.utxo.all_utxos().items():
            if utxo.pubkey_hash == wallet.pubkey_hash and utxo.asset_id == asset_id:
                inputs_list.append((txid, idx, utxo))
                total_in += utxo.portion

        if not inputs_list:
            raise ValueError(f"No UTXO found for asset {asset_id}")

        if total_in < portion:
            raise ValueError(f"Insufficient balance: have {total_in}, need {portion}")

        # 출력 생성
        outputs = [TxOutput(asset_id=asset_id, pubkey_hash=to_pubkey_hash, portion=portion)]

        # 거스름돈
        if total_in > portion:
            outputs.append(TxOutput(asset_id=asset_id, pubkey_hash=wallet.pubkey_hash, portion=total_in - portion))

        # 입력에 서명
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

    def refresh_pending_txs(self):
        """펜딩 트랜잭션 새로고침"""
        self.pending_tx_text.delete(1.0, tk.END)
        self.pending_tx_text.insert(tk.END, f"Pending Transactions: {len(self.pending_txs)}\n")
        self.pending_tx_text.insert(tk.END, "=" * 80 + "\n\n")

        for i, tx in enumerate(self.pending_txs):
            self.pending_tx_text.insert(tk.END, f"Transaction {i+1}:\n")
            self.pending_tx_text.insert(tk.END, f"  TXID: {tx.txid}\n")
            self.pending_tx_text.insert(tk.END, f"  Inputs: {len(tx.inputs)}\n")
            self.pending_tx_text.insert(tk.END, f"  Outputs: {len(tx.outputs)}\n")
            for j, out in enumerate(tx.outputs):
                asset_preview = out.asset_id[:16] + "..." if len(out.asset_id) > 16 else out.asset_id
                self.pending_tx_text.insert(tk.END, f"    Output {j}: Asset={asset_preview} Portion={out.portion}%\n")
            self.pending_tx_text.insert(tk.END, "\n")

    # ==================== 마이닝 관련 메서드 ====================

    def start_mining(self):
        """마이닝 시작"""
        if not self.pending_txs:
            messagebox.showerror("Error", "No pending transactions to mine")
            return

        # 백그라운드 스레드에서 마이닝
        def mine():
            self.mining_progress.start()
            self.log_mining("Starting mining process...")
            self.log_mining(f"Pending transactions: {len(self.pending_txs)}")

            try:
                block = self.blockchain.mine_block(self.pending_txs)

                # 채굴된 트랜잭션 제거
                mined_txids = {tx.txid for tx in block.txs}
                self.pending_txs = [
                    tx for tx in self.pending_txs
                    if tx.txid not in mined_txids
                ]

                self.log_mining(f"Block mined successfully!")
                self.log_mining(f"  Height: {block.header.height}")
                self.log_mining(f"  Hash: {block.header.hash()}")
                self.log_mining(f"  Nonce: {block.header.nonce}")
                self.log_mining(f"  Transactions: {len(block.txs)}")
                self.log_mining(f"  Remaining pending: {len(self.pending_txs)}")

                self.root.after(0, lambda: messagebox.showinfo("Success",
                    f"Block mined successfully!\nHeight: {block.header.height}"))

            except Exception as e:
                self.log_mining(f"Mining failed: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error",
                    f"Mining failed: {e}"))
            finally:
                self.mining_progress.stop()

        thread = threading.Thread(target=mine, daemon=True)
        thread.start()

    def log_mining(self, message: str):
        """마이닝 로그 출력"""
        def append():
            self.mining_log.insert(tk.END, f"{message}\n")
            self.mining_log.see(tk.END)
        self.root.after(0, append)

    # ==================== 자산 추적 관련 메서드 ====================

    def trace_asset(self):
        """자산 추적"""
        asset_id = self.asset_id_entry.get().strip()
        if not asset_id:
            messagebox.showerror("Error", "Please enter an asset ID")
            return

        history = self.da_chain.blockchain.trace_asset(asset_id)

        self.asset_trace_text.delete(1.0, tk.END)
        self.asset_trace_text.insert(tk.END, f"Asset Trace for: {asset_id}\n")
        self.asset_trace_text.insert(tk.END, "=" * 80 + "\n\n")

        if not history:
            self.asset_trace_text.insert(tk.END, "No transactions found for this asset\n")
        else:
            for height, block_hash, tx in history:
                self.asset_trace_text.insert(tk.END, f"Block Height: {height}\n")
                self.asset_trace_text.insert(tk.END, f"Block Hash: {block_hash}\n")
                self.asset_trace_text.insert(tk.END, f"TXID: {tx.txid}\n")
                self.asset_trace_text.insert(tk.END, f"Inputs: {len(tx.inputs)}\n")
                self.asset_trace_text.insert(tk.END, f"Outputs:\n")
                for i, out in enumerate(tx.outputs):
                    if out.asset_id == asset_id:
                        self.asset_trace_text.insert(tk.END,
                            f"  [{i}] To: {out.pubkey_hash[:16]}... Portion: {out.portion}%\n")
                self.asset_trace_text.insert(tk.END, "\n" + "-" * 80 + "\n\n")

    def run(self):
        """GUI 실행"""
        # 초기화: 제네시스 블록 생성 (없는 경우)
        if not self.blockchain.tip:
            self.initialize_genesis()

        # 초기 데이터 로드
        self.refresh_wallet_list()
        self.refresh_blockchain()
        self.refresh_pending_txs()

        self.root.mainloop()

    def initialize_genesis(self):
        """제네시스 블록 초기화"""
        # 기본 5개 자산으로 시작
        num_assets = 5
        initial_wallets = []

        for i in range(num_assets):
            wallet = Wallet()
            wallet_name = f"genesis-wallet-{i}"
            self.wallets[wallet_name] = wallet
            initial_wallets.append(wallet)

        genesis_block = create_genesis(num_assets, initial_wallets)
        self.blockchain.add_genesis_block(genesis_block)

        self.log_mining(f"Genesis block created with {num_assets} assets")
        self.log_mining(f"Created {num_assets} initial wallets")


def main():
    """GUI 메인 함수"""
    app = BlockchainGUI()
    app.run()


if __name__ == "__main__":
    main()
