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
