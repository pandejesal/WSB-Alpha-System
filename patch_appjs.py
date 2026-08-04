import re

with open("docs/js/app.js", "r") as f:
    content = f.read()

# Render SPY benchmark line in chart
chart_update_orig = """    // Draw Equity line
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
}"""

chart_update_new = """    // Draw SPY Benchmark line (if available)
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
}"""

# Need to store lastBacktestData to render SPY line
update_render = """function renderBacktestSection(data) {
    window.lastBacktestData = data;"""

content = content.replace("function renderBacktestSection(data) {", update_render)
content = content.replace(chart_update_orig, chart_update_new)

with open("docs/js/app.js", "w") as f:
    f.write(content)
