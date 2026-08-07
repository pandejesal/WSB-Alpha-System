with open("docs/index.html", "r") as f:
    content = f.read()

backtest_section = """
        <!-- Historical Backtest Section -->
        <section id="backtest-section" class="mt-8 mb-6">
            <h2 class="text-xl font-bold text-white mb-4">Historical Backtest (2019-2026)</h2>
            <div id="equity-chart" class="bg-gray-800 rounded-lg p-4 mb-4 border border-gray-700">
                <canvas id="equity-canvas" width="800" height="300" style="width: 100%; height: auto;"></canvas>
            </div>
            <div id="backtest-cards" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4"></div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <h3 class="text-sm font-semibold text-gray-400 uppercase mb-3">Yearly Performance</h3>
                    <div id="yearly-table"></div>
                </div>
                <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <h3 class="text-sm font-semibold text-gray-400 uppercase mb-3">Strategy Rankings (Top 10)</h3>
                    <div id="strategy-rankings"></div>
                </div>
            </div>
            <div id="overfitting-analysis" class="bg-gray-800 rounded-lg p-4 mt-4 border border-gray-700"></div>
        </section>
    </main>
"""
new_content = content.replace("    </main>", backtest_section)
with open("docs/index.html", "w") as f:
    f.write(new_content)
