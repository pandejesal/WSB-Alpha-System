// ============================================
// AUTHENTICATION - Password Protection
// ============================================

const DASHBOARD_HASH = 'f6f65a42898bffb0cc32e54496f8873b022a41dcd64b88aeacee2968e5740338';
const AUTH_KEY = 'wsb_dashboard_auth_hash';

async function hashPassword(password) {
    const msgBuffer = new TextEncoder().encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function checkAuth() {
    const auth = sessionStorage.getItem(AUTH_KEY);
    if (auth === DASHBOARD_HASH) return true;

    const input = prompt('Enter dashboard password:');
    if (input) {
        const hashedInput = await hashPassword(input);
        if (hashedInput === DASHBOARD_HASH) {
            sessionStorage.setItem(AUTH_KEY, hashedInput);
            return true;
        }
    }

    document.body.innerHTML = `
        <div class="min-h-screen bg-gray-900 flex items-center justify-center">
            <div class="bg-gray-800 p-8 rounded-lg border border-gray-700 text-center">
                <h1 class="text-2xl font-bold text-red-400 mb-4">Access Denied</h1>
                <p class="text-gray-400">Incorrect password.</p>
                <button onclick="sessionStorage.removeItem('${AUTH_KEY}'); location.reload();"
                        class="mt-4 px-4 py-2 bg-gray-700 rounded hover:bg-gray-600">
                    Try Again
                </button>
            </div>
        </div>`;
    return false;
}

// ============================================
// WSB-Alpha-System Dashboard
// ============================================

const DATA_BASE = 'data';

// Utility: show "—" if data is missing
function display(value, prefix = '', suffix = '') {
    if (value === null || value === undefined || value === '') return '—';
    return `${prefix}${value}${suffix}`;
}

// Utility: format currency
function formatCurrency(value) {
    if (value === null || value === undefined) return '—';
    return '$' + Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Utility: format percentage
function formatPercent(value) {
    if (value === null || value === undefined) return '—';
    return (Number(value) * 100).toFixed(2) + '%';
}

// Utility: color class based on value
function pnlClass(value) {
    if (value > 0) return 'text-green-400';
    if (value < 0) return 'text-red-400';
    return 'text-gray-400';
}

// ============================================
// LOAD AND DISPLAY DATA
// ============================================

async function loadPortfolio() {
    try {
        const resp = await fetch(`${DATA_BASE}/portfolio.json`);
        if (!resp.ok) throw new Error('No data');
        return await resp.json();
    } catch (e) {
        console.warn('portfolio.json not found:', e.message);
        return null;
    }
}

async function loadApiHealth() {
    try {
        const resp = await fetch(`${DATA_BASE}/apiHealth.json`);
        if (!resp.ok) throw new Error('No data');
        return await resp.json();
    } catch (e) {
        console.warn('apiHealth.json not found:', e.message);
        return null;
    }
}

async function loadStrategies() {
    try {
        const resp = await fetch(`${DATA_BASE}/strategies.json`);
        if (!resp.ok) throw new Error('No data');
        return await resp.json();
    } catch (e) {
        console.warn('strategies.json not found:', e.message);
        return null;
    }
}

async function loadTrades() {
    try {
        const resp = await fetch(`${DATA_BASE}/trades.json`);
        if (!resp.ok) throw new Error('No data');
        return await resp.json();
    } catch (e) {
        console.warn('trades.json not found:', e.message);
        return null;
    }
}

// ============================================
// RENDER FUNCTIONS
// ============================================

async function renderDashboard() {
    const portfolio = await loadPortfolio();
    const health = await loadApiHealth();
    const strategies = await loadStrategies();
    const trades = await loadTrades();

    // Portfolio cards
    if (portfolio) {
        document.getElementById('equity').textContent = formatCurrency(portfolio.equity);
        document.getElementById('equity-change').textContent = formatPercent(portfolio.total_pnl_pct / 100);
        document.getElementById('equity-change').className = `text-sm ${pnlClass(portfolio.total_pnl)}`;

        document.getElementById('daily-pnl').textContent = (portfolio.daily_pnl >= 0 ? '+' : '') + formatCurrency(portfolio.daily_pnl);
        document.getElementById('daily-pnl').className = `text-3xl font-bold ${pnlClass(portfolio.daily_pnl)}`;

        document.getElementById('win-rate').textContent = formatPercent(portfolio.win_rate);
        document.getElementById('total-trades').textContent = `${portfolio.total_trades} trades`;

        document.getElementById('regime-text').textContent = portfolio.regime.replace('_', ' ').toUpperCase();
        document.getElementById('gk-vol').textContent = `GK-Vol: ${portfolio.regime_gk_vol}`;

        // Open positions table
        const posBody = document.getElementById('positions-table');
        posBody.innerHTML = '';
        if (portfolio.open_positions && portfolio.open_positions.length > 0) {
            portfolio.open_positions.forEach(p => {
                posBody.innerHTML += `
                    <tr class="border-b border-gray-700">
                        <td class="py-2">${p.ticker}</td>
                        <td class="py-2 text-right">${p.qty}</td>
                        <td class="py-2 text-right">${formatCurrency(p.entry_price)}</td>
                        <td class="py-2 text-right">${formatCurrency(p.current_price)}</td>
                        <td class="py-2 text-right ${pnlClass(p.unrealized_pl)}">${p.unrealized_pl >= 0 ? '+' : ''}${formatCurrency(p.unrealized_pl)}</td>
                    </tr>`;
            });
        } else {
            posBody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-500">No open positions</td></tr>';
        }
    } else {
        // No data — show placeholders
        document.getElementById('equity').textContent = '—';
        document.getElementById('equity-change').textContent = 'No data';
        document.getElementById('daily-pnl').textContent = '—';
        document.getElementById('win-rate').textContent = '—';
        document.getElementById('regime-text').textContent = '—';
    }

    // API Health
    if (health && health.apis) {
        const healthDiv = document.getElementById('api-health');
        healthDiv.innerHTML = '';

        const apiOrder = ['alpaca', 'gemini', 'telegram', 'yfinance', 'reddit'];
        const apiNames = { alpaca: 'Alpaca Paper', gemini: 'Gemini API', telegram: 'Telegram Bot', yfinance: 'yfinance', reddit: 'Reddit API' };
        const statusColors = { connected: 'bg-green-500', error: 'bg-red-500', rate_limited: 'bg-yellow-500', not_configured: 'bg-gray-500' };

        apiOrder.forEach(api => {
            const data = health.apis[api] || { status: 'unknown', message: 'No data' };
            const color = statusColors[data.status] || 'bg-gray-500';
            const timeDiff = data.last_check ? getTimeDiff(data.last_check) : '—';

            healthDiv.innerHTML += `
                <div class="flex items-center justify-between py-2 border-b border-gray-700">
                    <div class="flex items-center space-x-3">
                        <span class="w-3 h-3 rounded-full ${color}"></span>
                        <span class="font-medium">${apiNames[api] || api}</span>
                    </div>
                    <div class="text-right">
                        <span class="text-sm text-gray-400">${data.message}</span>
                        <span class="text-xs text-gray-500 ml-2">${timeDiff}</span>
                    </div>
                </div>`;
        });
    }

    // Strategy leaderboard
    if (strategies && strategies.strategies) {
        const stratBody = document.getElementById('strategy-table');
        stratBody.innerHTML = '';

        const sorted = strategies.strategies.sort((a, b) => b.sharpe - a.sharpe).slice(0, 5);
        sorted.forEach((s, i) => {
            stratBody.innerHTML += `
                <tr class="border-b border-gray-700">
                    <td class="py-2">${i + 1}</td>
                    <td class="py-2">${s.name}</td>
                    <td class="py-2 text-right ${pnlClass(s.sharpe - 1)}">${s.sharpe.toFixed(2)}</td>
                    <td class="py-2 text-right">${s.fitness.toFixed(3)}</td>
                    <td class="py-2 text-right">${s.thompson_ev.toFixed(3)}</td>
                </tr>`;
        });
    }

    // Recent trades
    if (trades && trades.trades) {
        const tradesBody = document.getElementById('trades-table');
        tradesBody.innerHTML = '';

        const recent = trades.trades.slice(-10).reverse();
        recent.forEach(t => {
            tradesBody.innerHTML += `
                <tr class="border-b border-gray-700">
                    <td class="py-2">${t.date}</td>
                    <td class="py-2">${t.ticker}</td>
                    <td class="py-2 ${t.side === 'buy' ? 'text-green-400' : 'text-red-400'}">${t.side.toUpperCase()}</td>
                    <td class="py-2 text-right ${pnlClass(t.pnl)}">${t.pnl >= 0 ? '+' : ''}${formatCurrency(t.pnl)}</td>
                </tr>`;
        });
    }
}

function getTimeDiff(isoString) {
    const diff = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

// ============================================
// PAPER TRADING TOGGLE
// ============================================

async function togglePaperTrading(enable) {
    const token = localStorage.getItem('github_token');
    if (!token) {
        const input = prompt('Enter your GitHub personal access token (repo scope):');
        if (!input) return;
        localStorage.setItem('github_token', input);
    }

    const storedToken = localStorage.getItem('github_token');
    const repo = 'pandejesal/WSB-Alpha-System';

    try {
        // Get workflow ID
        const workflowsResp = await fetch(`https://api.github.com/repos/${repo}/actions/workflows`, {
            headers: { 'Authorization': `token ${storedToken}` }
        });

        if (!workflowsResp.ok) {
            alert('Failed to access GitHub API. Check your token.');
            localStorage.removeItem('github_token');
            return;
        }

        const workflowsData = await workflowsResp.json();
        const workflow = workflowsData.workflows.find(w => w.path === '.github/workflows/paper_trade.yml');

        if (!workflow) {
            alert('paper_trade.yml workflow not found');
            return;
        }

        // Trigger workflow
        const resp = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${workflow.id}/dispatches`, {
            method: 'POST',
            headers: {
                'Authorization': `token ${storedToken}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ref: 'main',
                inputs: { enabled: enable ? 'true' : 'false' }
            })
        });

        if (resp.ok || resp.status === 204) {
            alert(`Paper trading ${enable ? 'ENABLED' : 'DISABLED'}.\nWorkflow will run shortly.`);
            setTimeout(() => location.reload(), 2000);
        } else {
            const err = await resp.json();
            alert(`Failed: ${err.message || 'Unknown error'}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    if (!await checkAuth()) {
        return;
    }
    renderDashboard();

    // Refresh every 5 minutes
    setInterval(renderDashboard, 5 * 60 * 1000);
});
