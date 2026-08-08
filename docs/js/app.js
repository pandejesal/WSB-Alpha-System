// Vanilla JS for WSB Alpha System Dashboard - Overhaul V1
const DATA_PATHS = {
    portfolio: 'data/portfolio.json',
    strategies: 'data/strategies.json',
    trades: 'data/trades.json'
};

async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`Could not fetch ${url}:`, error);
        return null;
    }
}

function updatePortfolioMetrics(data) {
    if (!data) return;

    document.getElementById('equity').textContent = `$${data.equity?.toFixed(2) || '---'}`;

    document.getElementById('wf-efficiency').textContent = data.wf_efficiency ? data.wf_efficiency.toFixed(2) : '---';
    document.getElementById('wf-status').textContent = data.wf_efficiency >= 0.7 ? "Robust" : "Overfit";
    if (data.wf_efficiency >= 0.7) {
        document.getElementById('wf-status').classList.add('text-green-400');
    } else {
        document.getElementById('wf-status').classList.add('text-red-400');
    }

    document.getElementById('monte-carlo-p').textContent = data.oos_p_value ? data.oos_p_value.toFixed(4) : '---';
    document.getElementById('regime-text').textContent = data.regime || 'NORMAL';

    document.getElementById('active-hypothesis').textContent = data.active_hypothesis || '---';
    document.getElementById('hypothesis-confidence').textContent = data.hypothesis_confidence ? `Confidence: ${data.hypothesis_confidence}` : '---';
}

function updatePositions(data) {
    const table = document.getElementById('positions-table');
    if (!data || !data.positions || data.positions.length === 0) {
        table.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-500">No open positions</td></tr>';
        return;
    }

    table.innerHTML = data.positions.map(p => `
        <tr class="border-b border-gray-800 hover:bg-gray-800/50">
            <td class="py-2 font-medium">${p.symbol}</td>
            <td class="py-2 text-right">${p.qty}</td>
            <td class="py-2 text-right">$${p.entry_price?.toFixed(2) || '---'}</td>
            <td class="py-2 text-right">$${p.current_price?.toFixed(2) || '---'}</td>
            <td class="py-2 text-right ${p.unrealized_pl >= 0 ? 'text-green-400' : 'text-red-400'}">
                $${p.unrealized_pl?.toFixed(2) || '0.00'}
            </td>
        </tr>
    `).join('');
}

function updateStrategies(data) {
    const table = document.getElementById('strategy-table');
    if (!data || !data.population || data.population.length === 0) {
        table.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-gray-500">No active strategies</td></tr>';
        return;
    }

    // Filter and sort by OOS Sharpe, simulating the rigor filter
    const topStrats = data.population
        .sort((a, b) => (b.metrics?.oos_sharpe || 0) - (a.metrics?.oos_sharpe || 0))
        .slice(0, 5);

    table.innerHTML = topStrats.map((s, i) => `
        <tr class="border-b border-gray-800 hover:bg-gray-800/50">
            <td class="py-2 text-gray-400">${i + 1}</td>
            <td class="py-2 truncate max-w-[150px]" title="${s.name || s.id}">${s.name || s.id}</td>
            <td class="py-2 text-right text-green-400">${s.metrics?.oos_sharpe?.toFixed(2) || '---'}</td>
            <td class="py-2 text-right">${s.metrics?.oos_p_value?.toFixed(4) || '---'}</td>
            <td class="py-2 text-right text-gray-400">${s.parameters ? Object.keys(s.parameters).length : 0} params</td>
        </tr>
    `).join('');
}

function updateTrades(data) {
    const table = document.getElementById('trades-table');
    if (!data || !data.trades || data.trades.length === 0) {
        table.innerHTML = '<tr><td colspan="4" class="py-4 text-center text-gray-500">No recent trades</td></tr>';
        return;
    }

    table.innerHTML = data.trades.slice(0, 5).map(t => `
        <tr class="border-b border-gray-800 hover:bg-gray-800/50">
            <td class="py-2 font-medium">${t.date || '---'}</td>
            <td class="py-2 font-medium">${t.symbol}</td>
            <td class="py-2 text-left">${t.side}</td>
            <td class="py-2 text-right ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}">
                $${t.pnl?.toFixed(2) || '0.00'}
            </td>
        </tr>
    `).join('');
}

async function refreshDashboard() {
    const [portfolioData, strategyData, tradesData] = await Promise.all([
        fetchData(DATA_PATHS.portfolio),
        fetchData(DATA_PATHS.strategies),
        fetchData(DATA_PATHS.trades)
    ]);

    updatePortfolioMetrics(portfolioData);
    updatePositions(portfolioData);
    updateStrategies(strategyData);
    updateTrades(tradesData);
}

// Initial Load
refreshDashboard();
// Auto-refresh every 60 seconds
setInterval(refreshDashboard, 60000);



function renderBacktestSection(data) {
    // 1. Cards
    const cardsDiv = document.getElementById('backtest-cards');
    if (cardsDiv) {
        cardsDiv.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <p class="text-gray-400 text-xs uppercase">Final Equity</p>
                <p class="text-2xl font-bold text-green-400">${formatCurrency(data.portfolio_summary.final_equity)}</p>
                <p class="text-xs text-gray-400">Total Return: ${formatPercent(data.portfolio_summary.total_return_pct / 100)}</p>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <p class="text-gray-400 text-xs uppercase">CAGR</p>
                <p class="text-2xl font-bold">${formatPercent(data.portfolio_summary.cagr / 100)}</p>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <p class="text-gray-400 text-xs uppercase">Max Drawdown</p>
                <p class="text-2xl font-bold text-red-400">-${formatPercent(data.portfolio_summary.max_drawdown_pct / 100)}</p>
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

            const sumRet = years[y].returns.reduce((acc, r) => {
                return (1 + acc) * (1 + (r/100)) - 1;
            }, 0) * 100;

            tbody += `
                <tr class="border-b border-gray-700">
                    <td class="py-2">${y}</td>
                    <td class="py-2 text-right ${sumRet >= 0 ? 'text-green-400' : 'text-red-400'}">${sumRet > 0 ? '+' : ''}${formatPercent(sumRet / 100)}</td>
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
        const top10 = data.all_strategies.sort((a,b) => b.metrics.sharpe - a.metrics.sharpe).slice(0, 10);
        let tbody = '';
        top10.forEach((s, i) => {
            tbody += `
                <tr class="border-b border-gray-700">
                    <td class="py-2">${i+1}</td>
                    <td class="py-2 text-xs truncate max-w-[150px]" title="${s.name}">${s.name.replace('HA_MACD_RSI_BB_', '')}</td>
                    <td class="py-2 text-right">${formatPercent(s.metrics.total_return_pct / 100)}</td>
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

    ctx.fillStyle = '#6B7280';
    ctx.fillRect(padding.left + 120, padding.top, 10, 10);
    ctx.fillStyle = '#D1D5DB';
    ctx.fillText('Total Deposits', padding.left + 135, padding.top + 9);
}
