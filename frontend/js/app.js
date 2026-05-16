/**
 * EGX Data Engine - Frontend Application
 * تطبيق الواجهة الأمامية
 */

// Configuration
const API_BASE = window.location.origin;
const API_ENDPOINTS = {
    health: '/api/health',
    stats: '/api/stats',
    stocks: '/api/stocks',
    recommendations: '/api/recommendations',
    sectors: '/api/sectors',
    crypto: '/api/crypto',
    gold: '/api/gold',
    sources: '/api/sources',
    marketSummary: '/api/market/summary',
    syncStocks: '/api/sync/stocks',
    computeIndicators: '/api/compute/indicators'
};

// State
const state = {
    stocks: [],
    recommendations: [],
    currentPage: 1,
    itemsPerPage: 20
};

// ==================== API Functions ====================

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { success: false, error: error.message };
    }
}

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    checkServerStatus();
    loadDashboard();
    loadStocks();
    loadRecommendations();
    loadCrypto();
    loadGold();
    loadSources();
    
    // تحديث دوري كل 5 دقائق
    setInterval(checkServerStatus, 300000);
});

// ==================== Tabs ====================

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            
            // إزالة active من كل التبويبات
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // تفعيل التبويب المحدد
            tab.classList.add('active');
            const tabId = tab.dataset.tab;
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// ==================== Server Status ====================

async function checkServerStatus() {
    const statusBadge = document.getElementById('server-status');
    
    const result = await fetchAPI(API_ENDPOINTS.health);
    
    if (result.success || result.status === 'healthy') {
        statusBadge.textContent = '🟢 متصل';
        statusBadge.classList.add('online');
    } else {
        statusBadge.textContent = '🔴 غير متصل';
        statusBadge.classList.remove('online');
    }
}

// ==================== Dashboard ====================

async function loadDashboard() {
    // تحميل الإحصائيات
    const stats = await fetchAPI(API_ENDPOINTS.stats);
    
    if (stats.success && stats.data) {
        document.getElementById('stocks-count').textContent = stats.data.stocks_count || 0;
        document.getElementById('history-count').textContent = formatNumber(stats.data.history_count || 0);
        document.getElementById('buy-count').textContent = stats.data.signals?.buy || 0;
        document.getElementById('sell-count').textContent = stats.data.signals?.sell || 0;
        document.getElementById('hold-count').textContent = stats.data.signals?.hold || 0;
        
        if (stats.data.last_update) {
            document.getElementById('last-update').textContent = 
                `آخر تحديث: ${formatDate(stats.data.last_update)}`;
        }
    }
    
    // تحميل ملخص السوق
    const summary = await fetchAPI(API_ENDPOINTS.marketSummary);
    
    if (summary.success && summary.data) {
        const sentimentEl = document.getElementById('sentiment-value');
        sentimentEl.textContent = summary.data.sentiment === 'bullish' ? '📈 صاعد' : 
                                   summary.data.sentiment === 'bearish' ? '📉 هابط' : '➡️ محايد';
        sentimentEl.className = `sentiment-value ${summary.data.sentiment}`;
        
        // أفضل فرص الشراء
        if (summary.data.top_buy) {
            renderTable('top-buy-body', summary.data.top_buy, (item) => `
                <tr>
                    <td><strong>${item.ticker}</strong></td>
                    <td>${formatPrice(item.price)}</td>
                    <td>-</td>
                    <td>${item.confidence}%</td>
                </tr>
            `);
        }
        
        // أفضل فرص البيع
        if (summary.data.top_sell) {
            renderTable('top-sell-body', summary.data.top_sell, (item) => `
                <tr>
                    <td><strong>${item.ticker}</strong></td>
                    <td>${formatPrice(item.price)}</td>
                    <td>${item.confidence}%</td>
                    <td>-</td>
                </tr>
            `);
        }
    }
}

// ==================== Stocks ====================

async function loadStocks() {
    const result = await fetchAPI(`${API_ENDPOINTS.stocks}?limit=1000`);
    
    if (result.success && result.data) {
        state.stocks = result.data;
        renderStocks();
        populateSectorFilter();
    }
}

function renderStocks() {
    const start = (state.currentPage - 1) * state.itemsPerPage;
    const end = start + state.itemsPerPage;
    
    let stocks = state.stocks;
    
    // فلترة حسب القطاع
    const sector = document.getElementById('sector-filter')?.value;
    if (sector) {
        stocks = stocks.filter(s => s.sector === sector);
    }
    
    // بحث
    const search = document.getElementById('stock-search')?.value?.toLowerCase();
    if (search) {
        stocks = stocks.filter(s => 
            s.ticker?.toLowerCase().includes(search) || 
            s.name?.toLowerCase().includes(search) ||
            s.name_ar?.includes(search)
        );
    }
    
    const pageStocks = stocks.slice(start, end);
    
    renderTable('stocks-body', pageStocks, (stock) => `
        <tr>
            <td><strong>${stock.ticker}</strong></td>
            <td>${stock.name || stock.name_ar || '-'}</td>
            <td>${formatPrice(stock.price)}</td>
            <td class="${stock.change >= 0 ? 'price-up' : 'price-down'}">
                ${stock.change_percent >= 0 ? '+' : ''}${stock.change_percent?.toFixed(2)}%
            </td>
            <td>${stock.sector || '-'}</td>
        </tr>
    `);
    
    renderPagination('stocks-pagination', stocks.length, state.currentPage, (page) => {
        state.currentPage = page;
        renderStocks();
    });
}

function populateSectorFilter() {
    const sectors = [...new Set(state.stocks.map(s => s.sector).filter(Boolean))].sort();
    const select = document.getElementById('sector-filter');
    
    if (select) {
        sectors.forEach(sector => {
            const option = document.createElement('option');
            option.value = sector;
            option.textContent = sector;
            select.appendChild(option);
        });
    }
}

function filterStocks() {
    state.currentPage = 1;
    renderStocks();
}

function searchStocks() {
    state.currentPage = 1;
    renderStocks();
}

// ==================== Recommendations ====================

async function loadRecommendations(action = '') {
    const url = action ? `${API_ENDPOINTS.recommendations}?action=${action}` : API_ENDPOINTS.recommendations;
    const result = await fetchAPI(url);
    
    if (result.success && result.data) {
        state.recommendations = result.data;
        renderRecommendations();
    }
}

function renderRecommendations() {
    renderTable('recommendations-body', state.recommendations, (rec) => `
        <tr>
            <td><strong>${rec.ticker}</strong></td>
            <td>${formatPrice(rec.price)}</td>
            <td>${formatPrice(rec.target_1)}</td>
            <td>${formatPrice(rec.target_2)}</td>
            <td>${formatPrice(rec.stop_loss)}</td>
            <td>${rec.confidence}%</td>
            <td><span class="badge badge-${rec.action.toLowerCase()}">${rec.action}</span></td>
        </tr>
    `);
}

function filterRecommendations() {
    const action = document.getElementById('action-filter')?.value;
    loadRecommendations(action);
}

// ==================== Crypto ====================

async function loadCrypto() {
    const result = await fetchAPI(API_ENDPOINTS.crypto);
    
    if (result.success && result.data) {
        renderTable('crypto-body', result.data, (coin) => `
            <tr>
                <td><strong>${coin.ticker.toUpperCase()}</strong></td>
                <td>$${formatPrice(coin.price)}</td>
                <td>${formatDate(coin.date)}</td>
            </tr>
        `);
    }
}

// ==================== Gold ====================

async function loadGold() {
    const result = await fetchAPI(API_ENDPOINTS.gold);
    
    if (result.success && result.data) {
        renderTable('gold-body', result.data, (gold) => `
            <tr>
                <td><strong>${gold.karat} عيار</strong></td>
                <td>${formatPrice(gold.price)} ج.م</td>
                <td class="${gold.change >= 0 ? 'price-up' : 'price-down'}">
                    ${gold.change >= 0 ? '+' : ''}${gold.change || 0}
                </td>
            </tr>
        `);
    }
}

// ==================== Sources ====================

async function loadSources() {
    const result = await fetchAPI(API_ENDPOINTS.sources);
    
    if (result.success && result.data) {
        const container = document.getElementById('sources-grid');
        container.innerHTML = result.data.map(source => `
            <div class="source-card">
                <div class="source-name">${source.name}</div>
                <div class="source-url">${source.url}</div>
                <div class="source-meta">
                    <span class="source-type">${source.type}</span>
                    <span class="source-status ${source.status}">
                        ${source.status === 'online' ? '🟢 متصل' : '🔴 غير متصل'}
                    </span>
                </div>
                ${source.limit ? `<div class="source-limit">الحد: ${source.limit}</div>` : ''}
            </div>
        `).join('');
    }
}

// ==================== Actions ====================

async function refreshData() {
    showToast('جاري تحديث البيانات...', 'info');
    await loadDashboard();
    await loadStocks();
    await loadRecommendations();
    showToast('تم تحديث البيانات بنجاح', 'success');
}

async function syncStocks() {
    showToast('جاري المزامنة من الموقع...', 'info');
    const result = await fetchAPI(API_ENDPOINTS.syncStocks, { method: 'POST' });
    
    if (result.success) {
        showToast(result.message || 'تمت المزامنة بنجاح', 'success');
        await loadStocks();
    } else {
        showToast('فشلت المزامنة: ' + result.error, 'error');
    }
}

async function computeIndicators() {
    showToast('جاري حساب التحليلات الفنية...', 'info');
    const result = await fetchAPI(API_ENDPOINTS.computeIndicators, { method: 'POST' });
    
    if (result.success) {
        showToast(result.message || 'تم حساب التحليلات', 'success');
        await loadRecommendations();
        await loadDashboard();
    } else {
        showToast('فشل الحساب: ' + result.error, 'error');
    }
}

// ==================== Helpers ====================

function renderTable(tbodyId, data, rowTemplate) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="loading">لا توجد بيانات</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(rowTemplate).join('');
}

function renderPagination(containerId, total, current, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const pages = Math.ceil(total / state.itemsPerPage);
    
    if (pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous
    html += `<button ${current === 1 ? 'disabled' : ''} onclick="state.currentPage=${current-1};renderStocks()">←</button>`;
    
    // Pages
    for (let i = 1; i <= Math.min(pages, 5); i++) {
        html += `<button class="${current === i ? 'active' : ''}" onclick="state.currentPage=${i};renderStocks()">${i}</button>`;
    }
    
    // Next
    html += `<button ${current === pages ? 'disabled' : ''} onclick="state.currentPage=${current+1};renderStocks()">→</button>`;
    
    container.innerHTML = html;
}

function formatPrice(price) {
    if (price === null || price === undefined) return '-';
    return parseFloat(price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatNumber(num) {
    return num.toLocaleString('en-US');
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ar-EG', { year: 'numeric', month: 'short', day: 'numeric' });
}

// ==================== Toast Notifications ====================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // إزالة بعد 3 ثوان
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== Export for global access ====================

window.refreshData = refreshData;
window.syncStocks = syncStocks;
window.computeIndicators = computeIndicators;
window.filterStocks = filterStocks;
window.searchStocks = searchStocks;
window.filterRecommendations = filterRecommendations;
