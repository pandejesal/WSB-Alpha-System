import re

with open('docs/js/app.js', 'r') as f:
    content = f.read()

# Replace the Auth block
old_auth_block = """// ============================================
// AUTHENTICATION - Password Protection
// ============================================

const DASHBOARD_PASSWORD = 'WSB-Alpha-2026';  // Change this to your own password
const AUTH_KEY = 'wsb_dashboard_auth';

function checkAuth() {
    const auth = sessionStorage.getItem(AUTH_KEY);
    if (auth === DASHBOARD_PASSWORD) return true;

    const input = prompt('Enter dashboard password:');
    if (input === DASHBOARD_PASSWORD) {
        sessionStorage.setItem(AUTH_KEY, input);
        return true;
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

// Check auth before loading anything
if (!checkAuth()) {
    throw new Error('Unauthorized');
}"""

new_auth_block = """// ============================================
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
}"""

content = content.replace(old_auth_block, new_auth_block)

old_init_block = """document.addEventListener('DOMContentLoaded', () => {
    renderDashboard();

    // Refresh every 5 minutes
    setInterval(renderDashboard, 5 * 60 * 1000);
});"""

new_init_block = """document.addEventListener('DOMContentLoaded', async () => {
    if (!await checkAuth()) {
        return;
    }
    renderDashboard();

    // Refresh every 5 minutes
    setInterval(renderDashboard, 5 * 60 * 1000);
});"""

content = content.replace(old_init_block, new_init_block)

with open('docs/js/app.js', 'w') as f:
    f.write(content)
