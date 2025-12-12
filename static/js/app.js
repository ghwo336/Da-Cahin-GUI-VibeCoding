// DaBlockChain Web Interface JavaScript

let currentWallet = null;
let miningInterval = null;

// Tab Switching
document.addEventListener('DOMContentLoaded', function() {
    // Tab buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Initial load
    loadWallets();
    loadBlockchain();
    loadPendingTxs();
});

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Load data for tab
    if (tabName === 'wallets') loadWallets();
    if (tabName === 'visualizer') loadChainVisualizer();
    if (tabName === 'blockchain') loadBlockchain();
    if (tabName === 'transactions') loadPendingTxs();
}

function setStatus(message) {
    document.getElementById('status').textContent = message;
}

// ==================== Wallet Functions ====================

async function createWallet() {
    const name = document.getElementById('wallet-name').value.trim();
    if (!name) {
        alert('Please enter a wallet name');
        return;
    }

    try {
        const response = await fetch('/api/wallets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message);
            document.getElementById('wallet-name').value = '';
            loadWallets();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Failed to create wallet: ' + error);
    }
}

async function loadWallets() {
    try {
        const response = await fetch('/api/wallets');
        const wallets = await response.json();

        const container = document.getElementById('wallet-list');

        if (wallets.length === 0) {
            container.innerHTML = '<p class="loading">No wallets found. Create one!</p>';
            return;
        }

        let html = '<table><thead><tr><th>Name</th><th>Public Key Hash</th><th>Selected</th><th>Actions</th></tr></thead><tbody>';

        wallets.forEach(wallet => {
            const selected = wallet.selected ? '✓' : '';
            const selectedClass = wallet.selected ? 'selected-row' : '';

            html += `
                <tr class="${selectedClass}" style="cursor: pointer;" onclick="checkBalance('${wallet.name}')">
                    <td>${wallet.name}</td>
                    <td><code style="word-break: break-all; font-size: 0.85em;">${wallet.pubkey_hash}</code></td>
                    <td>${selected}</td>
                    <td onclick="event.stopPropagation()">
                        <button onclick="selectWallet('${wallet.name}')" class="btn btn-primary" style="padding: 5px 10px; font-size: 0.8em;">Select</button>
                        <button onclick="checkBalance('${wallet.name}')" class="btn btn-secondary" style="padding: 5px 10px; font-size: 0.8em;">Balance</button>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
        setStatus(`Loaded ${wallets.length} wallets`);
    } catch (error) {
        console.error('Failed to load wallets:', error);
    }
}

async function selectWallet(name) {
    try {
        const response = await fetch('/api/wallets/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        const data = await response.json();

        if (response.ok) {
            currentWallet = name;
            document.getElementById('tx-from').textContent = name;
            document.getElementById('tx-from').style.color = '#27ae60';
            loadWallets();
            alert(data.message);
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Failed to select wallet: ' + error);
    }
}

async function checkBalance(name) {
    console.log('Checking balance for:', name);

    try {
        const response = await fetch(`/api/wallets/balance?name=${encodeURIComponent(name)}`);
        const data = await response.json();

        console.log('Balance response:', data);

        if (response.ok) {
            const container = document.getElementById('balance-info');

            if (!container) {
                console.error('balance-info container not found!');
                alert('Error: Balance info container not found');
                return;
            }

            let html = `
                <h3 style="color: #2c3e50; margin-bottom: 15px;">💰 Balance for: ${data.wallet_name}</h3>
                <p style="margin: 10px 0;"><strong>Public Key Hash:</strong></p>
                <p style="background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; word-break: break-all; font-size: 0.9em;">${data.pubkey_hash}</p>
                <hr style="margin: 20px 0; border: none; border-top: 2px solid #3498db;">
            `;

            if (Object.keys(data.balances).length === 0) {
                html += '<p style="text-align: center; color: #7f8c8d; padding: 20px;">No assets found in this wallet</p>';
            } else {
                html += '<h4 style="color: #2c3e50; margin-bottom: 15px;">📊 Assets:</h4>';
                for (const [assetId, portion] of Object.entries(data.balances)) {
                    html += `
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <div style="font-size: 1.1em; margin-bottom: 8px;">
                                <strong>🪙 Asset ID:</strong> <span style="background: rgba(255,255,255,0.2); padding: 3px 8px; border-radius: 3px;">${assetId}</span>
                            </div>
                            <div style="font-size: 1.3em;">
                                <strong>📈 Amount:</strong> <span style="font-size: 1.5em; font-weight: bold;">${portion}%</span>
                            </div>
                        </div>
                    `;
                }
            }

            container.innerHTML = html;
            console.log('Balance info updated successfully');
        } else {
            console.error('Balance API error:', data.error);
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to check balance:', error);
        alert('Failed to check balance: ' + error.message);
    }
}

// ==================== Chain Visualizer Functions ====================

let selectedBlockHeight = null;

async function loadChainVisualizer() {
    // 3D visualizer가 있으면 3D로 로드, 없으면 2D로 로드
    const canvas3D = document.getElementById('chain-canvas-3d');
    const canvas2D = document.getElementById('chain-canvas');

    if (canvas3D) {
        // 3D visualizer exists, skip 2D loading
        return;
    }

    if (!canvas2D) {
        console.warn('No canvas element found for chain visualizer');
        return;
    }

    try {
        const response = await fetch('/api/blockchain');
        const blocks = await response.json();

        const container = canvas2D;

        if (blocks.length === 0) {
            container.innerHTML = '<p class="loading" style="color: white;">No blocks in blockchain</p>';
            return;
        }

        let html = '';

        // 블록들을 시각적으로 표현
        blocks.forEach((block, index) => {
            const isGenesis = block.height === 0;
            const isSelected = selectedBlockHeight === block.height;
            const blockClass = isGenesis ? 'genesis' : '';
            const selectedClass = isSelected ? 'selected' : '';

            html += `
                <div class="block-visual">
                    <div class="block-box ${blockClass} ${selectedClass}" onclick="selectBlockVisual(${block.height})">
                        <div class="block-header-visual">
                            <div class="block-height">#${block.height}</div>
                            <div class="block-label">${isGenesis ? '🌟 Genesis Block' : 'Block'}</div>
                        </div>
                        <div class="block-info">
                            <div style="margin-bottom: 10px;">
                                <strong>Hash:</strong><br>
                                <span class="block-hash-short">${block.hash.substring(0, 16)}...</span>
                            </div>
                            <div style="margin-bottom: 10px;">
                                <span class="block-tx-count">📦 ${block.tx_count} TX</span>
                            </div>
                            <div>
                                <strong>Nonce:</strong> ${block.nonce}
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // 화살표 추가 (마지막 블록 제외)
            if (index < blocks.length - 1) {
                html += '<div class="chain-arrow">→</div>';
            }
        });

        // 통계 추가
        html += `
            <div class="chain-stats">
                <h3>⛓️ Chain Statistics</h3>
                <p>Total Blocks: <strong>${blocks.length}</strong></p>
                <p>Total Transactions: <strong>${blocks.reduce((sum, b) => sum + b.tx_count, 0)}</strong></p>
                <p>Latest Block Height: <strong>#${blocks[blocks.length - 1].height}</strong></p>
            </div>
        `;

        container.innerHTML = html;

        // 마지막 블록으로 자동 스크롤
        setTimeout(() => {
            container.scrollLeft = container.scrollWidth;
        }, 100);

        setStatus(`Chain visualized: ${blocks.length} blocks`);
    } catch (error) {
        console.error('Failed to load chain visualizer:', error);
    }
}

async function selectBlockVisual(height) {
    selectedBlockHeight = height;

    // 비주얼 업데이트
    await loadChainVisualizer();

    // 블록 상세 정보 로드
    try {
        const response = await fetch(`/api/blockchain/block/${height}`);
        const block = await response.json();

        if (response.ok) {
            const container = document.getElementById('selected-block-info');
            let html = `
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 15px;">
                    <h3 style="color: white; margin-bottom: 15px;">Block #${block.height}</h3>
                    <p><strong>Hash:</strong><br><code style="background: rgba(0,0,0,0.2); padding: 5px; border-radius: 3px; word-break: break-all;">${block.hash}</code></p>
                    <p style="margin-top: 10px;"><strong>Previous Hash:</strong><br><code style="background: rgba(0,0,0,0.2); padding: 5px; border-radius: 3px; word-break: break-all;">${block.prev_hash}</code></p>
                    <p style="margin-top: 10px;"><strong>Merkle Root:</strong><br><code style="background: rgba(0,0,0,0.2); padding: 5px; border-radius: 3px; word-break: break-all;">${block.merkle_root}</code></p>
                    <p style="margin-top: 10px;"><strong>Nonce:</strong> ${block.nonce}</p>
                </div>
                <h4 style="color: #2c3e50; margin: 15px 0;">📦 Transactions (${block.transactions.length})</h4>
            `;

            block.transactions.forEach((tx, i) => {
                html += `
                    <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0;">
                        <h5 style="color: #667eea; margin-bottom: 10px;">Transaction ${i + 1}</h5>
                        <p style="font-size: 0.9em;"><strong>TXID:</strong> <code>${tx.txid.substring(0, 32)}...</code></p>
                        <p><strong>Inputs:</strong> ${tx.inputs}</p>
                        <p><strong>Outputs:</strong></p>
                `;

                tx.outputs.forEach((out, j) => {
                    html += `
                        <div style="background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 3px solid #667eea;">
                            <strong>Output ${j}:</strong>
                            Asset: <code>${out.asset_id}</code>,
                            Portion: <strong>${out.portion}%</strong>
                        </div>
                    `;
                });

                html += '</div>';
            });

            container.innerHTML = html;
        }
    } catch (error) {
        console.error('Failed to load block details:', error);
    }
}

// ==================== Blockchain Functions ====================

async function loadBlockchain() {
    try {
        const response = await fetch('/api/blockchain');
        const blocks = await response.json();

        const container = document.getElementById('block-list');

        if (blocks.length === 0) {
            container.innerHTML = '<p class="loading">No blocks in blockchain</p>';
            return;
        }

        let html = '<table><thead><tr><th>Height</th><th>Block Hash</th><th>Previous Hash</th><th>Txs</th><th>Nonce</th><th>Actions</th></tr></thead><tbody>';

        blocks.forEach(block => {
            html += `
                <tr>
                    <td>${block.height}</td>
                    <td><code>${block.hash.substring(0, 20)}...</code></td>
                    <td><code>${block.prev_hash.substring(0, 20)}...</code></td>
                    <td>${block.tx_count}</td>
                    <td>${block.nonce}</td>
                    <td>
                        <button onclick="viewBlock(${block.height})" class="btn btn-primary" style="padding: 5px 10px; font-size: 0.8em;">View</button>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
        setStatus(`Blockchain: ${blocks.length} blocks`);
    } catch (error) {
        console.error('Failed to load blockchain:', error);
    }
}

async function viewBlock(height) {
    try {
        const response = await fetch(`/api/blockchain/block/${height}`);
        const block = await response.json();

        if (response.ok) {
            const container = document.getElementById('block-details');
            let html = `
                <h3>Block #${block.height}</h3>
                <p><strong>Hash:</strong> <code>${block.hash}</code></p>
                <p><strong>Previous Hash:</strong> <code>${block.prev_hash}</code></p>
                <p><strong>Merkle Root:</strong> <code>${block.merkle_root}</code></p>
                <p><strong>Nonce:</strong> ${block.nonce}</p>
                <p><strong>Transactions:</strong> ${block.transactions.length}</p>
                <hr style="margin: 15px 0;">
                <h4>Transactions:</h4>
            `;

            block.transactions.forEach((tx, i) => {
                html += `
                    <div class="tx-item">
                        <h4>Transaction ${i + 1}</h4>
                        <p><strong>TXID:</strong> <code>${tx.txid.substring(0, 32)}...</code></p>
                        <p><strong>Inputs:</strong> ${tx.inputs}</p>
                        <p><strong>Outputs:</strong></p>
                `;

                tx.outputs.forEach((out, j) => {
                    html += `
                        <div style="background: #ecf0f1; padding: 8px; margin: 5px 0; border-radius: 3px;">
                            Output ${j}: Asset=${out.asset_id}, Portion=${out.portion}%
                        </div>
                    `;
                });

                html += '</div>';
            });

            container.innerHTML = html;
        } else {
            alert('Error: ' + block.error);
        }
    } catch (error) {
        alert('Failed to load block: ' + error);
    }
}

// ==================== Transaction Functions ====================

async function createTransaction() {
    if (!currentWallet) {
        alert('Please select a wallet first');
        return;
    }

    const to = document.getElementById('tx-to').value.trim();
    const asset = document.getElementById('tx-asset').value.trim();
    const portion = document.getElementById('tx-portion').value;

    if (!to || !asset || !portion) {
        alert('Please fill all fields');
        return;
    }

    try {
        const response = await fetch('/api/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                to_pubkey_hash: to,
                asset_id: asset,
                portion: parseInt(portion)
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert(`Transaction created successfully!\nTXID: ${data.txid}`);
            document.getElementById('tx-to').value = '';
            document.getElementById('tx-asset').value = '';
            document.getElementById('tx-portion').value = '';
            loadPendingTxs();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Failed to create transaction: ' + error);
    }
}

async function loadPendingTxs() {
    try {
        const response = await fetch('/api/transactions/pending');
        const txs = await response.json();

        const container = document.getElementById('pending-txs');

        if (txs.length === 0) {
            container.innerHTML = '<p class="loading">No pending transactions</p>';
            return;
        }

        let html = `<h3>Pending Transactions: ${txs.length}</h3><hr style="margin: 15px 0;">`;

        txs.forEach((tx, i) => {
            html += `
                <div class="tx-item">
                    <h4>Transaction ${i + 1}</h4>
                    <p><strong>TXID:</strong> <code>${tx.txid}</code></p>
                    <p><strong>Inputs:</strong> ${tx.inputs}</p>
                    <p><strong>Outputs:</strong></p>
            `;

            tx.outputs.forEach((out, j) => {
                const assetPreview = out.asset_id.length > 20 ? out.asset_id.substring(0, 20) + '...' : out.asset_id;
                html += `
                    <div style="background: #ecf0f1; padding: 8px; margin: 5px 0; border-radius: 3px;">
                        Output ${j}: Asset=${assetPreview}, Portion=${out.portion}%
                    </div>
                `;
            });

            html += '</div>';
        });

        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load pending transactions:', error);
    }
}

// ==================== Mining Functions ====================

async function startMining() {
    try {
        const response = await fetch('/api/mine', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('mining-progress').style.display = 'block';
            document.getElementById('mining-log').innerHTML = '<p style="color: #00ff00;">Mining started...</p>';

            // Poll mining status
            miningInterval = setInterval(checkMiningStatus, 1000);
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Failed to start mining: ' + error);
    }
}

async function checkMiningStatus() {
    try {
        const response = await fetch('/api/mine/status');
        const status = await response.json();

        const logContainer = document.getElementById('mining-log');
        let html = '';

        status.log.forEach(line => {
            html += `<p style="color: #00ff00;">${line}</p>`;
        });

        logContainer.innerHTML = html;
        logContainer.scrollTop = logContainer.scrollHeight;

        if (!status.is_mining) {
            clearInterval(miningInterval);
            document.getElementById('mining-progress').style.display = 'none';
            loadBlockchain();
            loadPendingTxs();
        }
    } catch (error) {
        console.error('Failed to check mining status:', error);
    }
}

// ==================== Asset Trace Functions ====================

async function traceAsset() {
    const assetId = document.getElementById('asset-id').value.trim();

    if (!assetId) {
        alert('Please enter an asset ID');
        return;
    }

    try {
        const response = await fetch(`/api/trace/${assetId}`);
        const history = await response.json();

        const container = document.getElementById('asset-history');

        if (history.length === 0) {
            container.innerHTML = '<p class="loading">No transactions found for this asset</p>';
            return;
        }

        let html = `<h3>Asset Trace: ${assetId}</h3><hr style="margin: 15px 0;">`;

        history.forEach((item, i) => {
            html += `
                <div class="trace-item">
                    <h3>Transaction ${i + 1}</h3>
                    <p><strong>Block Height:</strong> ${item.height}</p>
                    <p><strong>Block Hash:</strong> <code>${item.block_hash.substring(0, 32)}...</code></p>
                    <p><strong>TXID:</strong> <code>${item.txid.substring(0, 32)}...</code></p>
                    <p><strong>Inputs:</strong></p>
            `;

            item.inputs.forEach((inp, j) => {
                html += `
                    <div style="background: #ecf0f1; padding: 8px; margin: 5px 0; border-radius: 3px;">
                        Input ${j}: (${inp.txid_ref.substring(0, 16)}..., ${inp.index})
                    </div>
                `;
            });

            html += '<p><strong>Outputs:</strong></p>';

            item.outputs.forEach((out, j) => {
                if (out.asset_id === assetId) {
                    html += `
                        <div class="output" style="background: #d5f4e6; padding: 10px; margin: 5px 0; border-radius: 3px; border-left: 4px solid #27ae60;">
                            Output ${j}: To=${out.pubkey_hash.substring(0, 20)}..., Portion=${out.portion}%
                        </div>
                    `;
                }
            });

            html += '</div>';
        });

        container.innerHTML = html;
    } catch (error) {
        alert('Failed to trace asset: ' + error);
    }
}
