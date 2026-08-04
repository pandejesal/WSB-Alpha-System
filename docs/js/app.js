
async function loadBacktestReport() {
    try {
        const resp = await fetch(`${DATA_BASE}/backtest_report.json`);
        if (!resp.ok) throw new Error('No data');
        return await resp.json();
    } catch (e) {
        console.warn('backtest_report.json not found:', e.message);
        return null;
    }
}

// ============================================
// AUTHENTICATION - Password Protection

async function loadBacktestReport() {
    try {
        const resp = await fetch(`${DATA_BASE}/backtest_report.json`);
        if (!resp.ok) throw new Error('No data');
        return await resp.json();
    } catch (e) {
        console.warn('backtest_report.json not found:', e.message);
        return null;
    }
}

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
    return Number(value).toFixed(2) + '%';
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

    const backtest = await loadBacktestReport();
    if (backtest) {
        renderBacktestSection(backtest);
    }


    // Portfolio cards
    if (portfolio) {
        document.getElementById('equity').textContent = formatCurrency(portfolio.equity);
        document.getElementById('equity-change').textContent = formatPercent(portfolio.total_pnl_pct);
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



function renderBacktestSection(data) {
    window.lastBacktestData = data;
    // 1. Cards
    const cardsDiv = document.getElementById('backtest-cards');
    if (cardsDiv) {
        cardsDiv.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <p class="text-gray-400 text-xs uppercase">Final Equity</p>
                <p class="text-2xl font-bold text-green-400">${formatCurrency(data.portfolio_summary.final_equity)}</p>
                <p class="text-xs text-gray-400">Total Return: ${data.portfolio_summary.total_return_pct.toFixed(2)}%</p>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <p class="text-gray-400 text-xs uppercase">CAGR</p>
                <p class="text-2xl font-bold">${data.portfolio_summary.cagr.toFixed(2)}%</p>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <p class="text-gray-400 text-xs uppercase">Max Drawdown</p>
                <p class="text-2xl font-bold text-red-400">-${data.portfolio_summary.max_drawdown_pct.toFixed(2)}%</p>
                <p class="text-xs text-gray-400">On ${data.portfolio_summary.max_drawdown_date}</p>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <p class="text-gray-400 text-xs uppercase">Risk / Reward</p>
                <p class="text-2xl font-bold text-blue-400">Sharpe: ${data.portfolio_summary.sharpe_ratio.toFixed(2)}</p>
                <p class="text-xs text-gray-400">Sortino: ${data.portfolio_summary.sortino_ratio.toFixed(2)}</p>
            </div>
        `;
    }

    // 2. Yearly Table
    const yTable = document.getElementById('yearly-table');
    if (yTable && data.quarterly_returns) {
        let tbody = '';
        // Group by year
        const years = {};
        data.quarterly_returns.forEach(q => {
            const y = q.quarter.substring(0, 4);
            if (!years[y]) years[y] = { returns: [] };
            years[y].returns.push(q.return_pct);
        });

        Object.keys(years).forEach(y => {
            const sumRet = years[y].returns.reduce((a,b) => a+b, 0);
            tbody += `
                <tr class="border-b border-gray-700">
                    <td class="py-2">${y}</td>
                    <td class="py-2 text-right ${sumRet >= 0 ? 'text-green-400' : 'text-red-400'}">${sumRet > 0 ? '+' : ''}${sumRet.toFixed(2)}%</td>
                </tr>
            `;
        });

        yTable.innerHTML = `
            <table class="w-full text-sm">
                <thead>
                    <tr class="text-gray-500 border-b border-gray-700 text-xs">
                        <th class="text-left py-2">Year</th>
                        <th class="text-right py-2">Return</th>
                    </tr>
                </thead>
                <tbody>${tbody}</tbody>
            </table>
        `;
    }

    // 3. Strategy Rankings
    const sRankings = document.getElementById('strategy-rankings');
    if (sRankings && data.all_strategies) {
        const top10 = data.all_strategies.sort((a,b) => {
            const aScore = a.metrics.sharpe * Math.max(a.metrics.wf_efficiency, 0.1);
            const bScore = b.metrics.sharpe * Math.max(b.metrics.wf_efficiency, 0.1);
            return bScore - aScore;
        }).slice(0, 10);
        let tbody = '';
        top10.forEach((s, i) => {
            tbody += `
                <tr class="border-b border-gray-700">
                    <td class="py-2">${i+1}</td>
                    <td class="py-2 text-xs truncate max-w-[150px]" title="${s.name}">${s.name.replace('HA_MACD_RSI_BB_', '')}</td>
                    <td class="py-2 text-right">${s.metrics.total_return_pct.toFixed(2)}%</td>
                    <td class="py-2 text-right">${s.metrics.sharpe.toFixed(2)}</td>
                    <td class="py-2 text-right">
                        <span class="px-2 py-1 rounded text-[10px] ${s.metrics.likely_overfit ? 'bg-red-900 text-red-200' : 'bg-green-900 text-green-200'}">
                            ${s.metrics.likely_overfit ? 'OVERFIT' : 'ROBUST'}
                        </span>
                    </td>
                </tr>
            `;
        });

        sRankings.innerHTML = `
            <table class="w-full text-sm">
                <thead>
                    <tr class="text-gray-500 border-b border-gray-700 text-xs">
                        <th class="text-left py-2">#</th>
                        <th class="text-left py-2">Params</th>
                        <th class="text-right py-2">Return</th>
                        <th class="text-right py-2">Sharpe</th>
                        <th class="text-right py-2">Status</th>
                    </tr>
                </thead>
                <tbody>${tbody}</tbody>
            </table>
        `;
    }

    // 4. Overfitting summary
    const ov = document.getElementById('overfitting-analysis');
    if (ov) {
        const total = data.strategies_tested;
        const overfit = data.all_strategies.filter(s => s.metrics.likely_overfit).length;
        ov.innerHTML = `
            <h3 class="text-sm font-semibold text-gray-400 uppercase mb-3">Overfitting Analysis</h3>
            <div class="flex justify-between items-center">
                <div>
                    <p class="text-2xl font-bold">${((total - overfit) / total * 100).toFixed(0)}% Robust</p>
                    <p class="text-xs text-gray-400">${total - overfit} passed Walk-Forward checks out of ${total}</p>
                </div>
                <div class="text-right">
                    <p class="text-sm">Avg WF Efficiency: <span class="font-bold text-blue-400">${(data.all_strategies.reduce((a,b)=>a+b.metrics.wf_efficiency, 0) / total).toFixed(2)}</span></p>
                </div>
            </div>
        `;
    }

    // 5. Chart
    renderEquityChart(data.equity_curve);
}

function renderEquityChart(history) {
    const canvas = document.getElementById('equity-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!history || history.length === 0) return;

    const padding = { top: 20, right: 20, bottom: 30, left: 50 };
    const w = canvas.width - padding.left - padding.right;
    const h = canvas.height - padding.top - padding.bottom;

    const maxEq = Math.max(...history.map(d => Math.max(d.equity, d.deposits)));
    const minEq = Math.min(...history.map(d => Math.min(d.equity, d.deposits)));
    const range = maxEq - minEq || 1;

    function scaleX(i) {
        return padding.left + (i / (history.length - 1)) * w;
    }

    function scaleY(val) {
        return padding.top + h - ((val - minEq) / range) * h;
    }

    // Draw grid
    ctx.strokeStyle = '#374151'; // gray-700
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (i / 4) * h;
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + w, y);

        // labels
        ctx.fillStyle = '#9CA3AF'; // gray-400
        ctx.font = '10px sans-serif';
        const val = maxEq - (i / 4) * range;
        ctx.fillText('$' + val.toFixed(0), 5, y + 4);
    }
    ctx.stroke();

    // X labels (years)
    let lastYear = '';
    history.forEach((d, i) => {
        const year = d.date.substring(0, 4);
        if (year !== lastYear && i > 0) {
            const x = scaleX(i);
            ctx.fillText(year, x - 12, canvas.height - 10);

            // tick mark
            ctx.beginPath();
            ctx.moveTo(x, padding.top + h);
            ctx.lineTo(x, padding.top + h + 5);
            ctx.stroke();

            lastYear = year;
        } else if (i === 0) {
            lastYear = year;
        }
    });

    // Draw Deposits line
    ctx.strokeStyle = '#6B7280'; // gray-500
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    history.forEach((d, i) => {
        const x = scaleX(i);
        const y = scaleY(d.deposits);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw SPY Benchmark line (if available)
    if (window.lastBacktestData && window.lastBacktestData.benchmark_equity_curve) {
        ctx.strokeStyle = '#3B82F6'; // blue-500
        ctx.lineWidth = 2;
        ctx.beginPath();
        window.lastBacktestData.benchmark_equity_curve.forEach((d, i) => {
            const x = scaleX(i);
            const y = scaleY(d.equity);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }

    // Draw Equity line
    ctx.strokeStyle = '#4ADE80'; // green-400
    ctx.lineWidth = 2;
    ctx.beginPath();
    history.forEach((d, i) => {
        const x = scaleX(i);
        const y = scaleY(d.equity);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Legend
    ctx.fillStyle = '#4ADE80';
    ctx.fillRect(padding.left + 20, padding.top, 10, 10);
    ctx.fillStyle = '#D1D5DB';
    ctx.fillText('Portfolio Equity', padding.left + 35, padding.top + 9);

    ctx.fillStyle = '#3B82F6';
    ctx.fillRect(padding.left + 140, padding.top, 10, 10);
    ctx.fillStyle = '#D1D5DB';
    ctx.fillText('SPY Benchmark', padding.left + 155, padding.top + 9);

    ctx.fillStyle = '#6B7280';
    ctx.fillRect(padding.left + 260, padding.top, 10, 10);
    ctx.fillStyle = '#D1D5DB';
    ctx.fillText('Total Deposits', padding.left + 275, padding.top + 9);
}
