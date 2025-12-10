// ==========================================
// COINDCX FUTURES BOT - ENHANCED
// ==========================================

const SERVER = window.location.origin;

const State = {
    connected: false,
    coin: '',
    coinName: '',
    type: 'LONG',
    entry: 'MARKET',
    price: 0,
    leverage: 1,
    trade: null,
    socket: null,
    prices: {}
};

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    fetchPrices();
    setInterval(fetchPrices, 2000);
});

function initSocket() {
    try {
        State.socket = io(SERVER);
        
        State.socket.on('connect', () => {
            State.connected = true;
            updateStatus(true);
            log('Connected to server', 'success');
        });
        
        State.socket.on('disconnect', () => {
            State.connected = false;
            updateStatus(false);
            log('Disconnected', 'error');
        });
        
        State.socket.on('price_update', onPriceUpdate);
        State.socket.on('level_reached', onLevelReached);
        State.socket.on('trade_closed', onTradeClosed);
        State.socket.on('log', (data) => log(data.log.message, data.log.type));
    } catch (e) {
        console.error('Socket error:', e);
        // Fallback to polling
        setInterval(pollStatus, 3000);
    }
}

function updateStatus(ok) {
    const dot = document.querySelector('.dot');
    const text = document.getElementById('statusText');
    const server = document.getElementById('serverStatus');
    
    if (ok) {
        dot.classList.add('online');
        text.textContent = 'Connected';
        server.innerHTML = '<span style="color:#00ff88">✅ Server connected!</span>';
    } else {
        dot.classList.remove('online');
        text.textContent = 'Disconnected';
        server.innerHTML = '<span style="color:#ff4757">❌ Server offline</span>';
    }
}

// ==========================================
// PRICE FETCHING
// ==========================================

async function fetchPrices() {
    try {
        const res = await fetch(`${SERVER}/api/ticker`);
        const data = await res.json();
        
        if (!State.connected) updateStatus(true);
        
        // Build price map
        State.prices = {};
        data.forEach(t => {
            const market = t.market || '';
            const price = parseFloat(t.last_price) || 0;
            State.prices[market] = price;
            
            // Remove B- prefix for easier lookup
            if (market.startsWith('B-')) {
                const clean = market.replace('B-', '').replace('_', '');
                State.prices[clean] = price;
            }
        });
        
        // Update UI
        const pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT'];
        pairs.forEach(pair => {
            const price = getPrice(pair);
            const el = document.getElementById(`price-${pair}`);
            if (el && price) {
                el.textContent = formatPrice(price);
            }
            
            if (State.coin === pair && price) {
                State.price = price;
                document.getElementById('livePrice').textContent = `$${price.toLocaleString()}`;
            }
        });
        
        updateSummary();
        updateSLSuggestions();
        
    } catch (e) {
        console.error('Fetch error:', e);
        updateStatus(false);
    }
}

function getPrice(symbol) {
    // Try different formats
    const formats = [
        symbol,
        `B-${symbol.replace('USDT', '_USDT')}`,
        symbol.replace('USDT', '_USDT')
    ];
    
    for (const fmt of formats) {
        if (State.prices[fmt]) return State.prices[fmt];
    }
    
    return null;
}

function formatPrice(p) {
    if (!p) return '--';
    if (p >= 10000) return `$${(p/1000).toFixed(1)}K`;
    if (p >= 100) return `$${p.toFixed(2)}`;
    if (p >= 1) return `$${p.toFixed(3)}`;
    return `$${p.toFixed(6)}`;
}

// ==========================================
// COIN SELECTION
// ==========================================

function selectCoin(pair, name) {
    State.coin = pair;
    State.coinName = name;
    State.price = getPrice(pair) || 0;
    
    document.querySelectorAll('.coin').forEach(c => c.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
    
    document.getElementById('selectedCoin').classList.remove('hidden');
    document.getElementById('selectedName').textContent = `${name} Perpetual`;
    document.getElementById('livePrice').textContent = `$${State.price.toLocaleString()}`;
    
    document.getElementById('tradeCard').classList.remove('hidden');
    
    updateSLSuggestions();
    updateSummary();
    
    toast(`${name}/USDT selected`);
}

// ==========================================
// TRADE SETUP
// ==========================================

function setType(type) {
    State.type = type;
    
    const longBtn = document.getElementById('longBtn');
    const shortBtn = document.getElementById('shortBtn');
    
    longBtn.classList.toggle('active', type === 'LONG');
    shortBtn.classList.toggle('active', type === 'SHORT');
    shortBtn.classList.toggle('short', type === 'SHORT');
    
    document.getElementById('slHint').textContent = 
        type === 'LONG' ? 'Below entry' : 'Above entry';
    
    updateSLSuggestions();
    updateSummary();
}

function setEntry(type) {
    State.entry = type;
    document.getElementById('marketBtn').classList.toggle('active', type === 'MARKET');
    document.getElementById('limitBtn').classList.toggle('active', type === 'LIMIT');
    document.getElementById('entryField').classList.toggle('hidden', type === 'MARKET');
    updateSummary();
}

function setLeverage(lev) {
    State.leverage = lev;
    document.getElementById('leverage').value = lev;
    
    document.querySelectorAll('.lev-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`lev${lev}`).classList.add('active');
    
    updateSummary();
}

function useLive() {
    document.getElementById('entryPrice').value = State.price;
    updateSummary();
}

function updateSLSuggestions() {
    if (!State.price) return;
    
    const container = document.getElementById('slSuggestions');
    const isLong = State.type === 'LONG';
    
    const suggestions = [
        { pct: 1, label: '1%' },
        { pct: 2, label: '2%' },
        { pct: 3, label: '3%' },
        { pct: 5, label: '5%' }
    ];
    
    container.innerHTML = suggestions.map(s => {
        const sl = isLong 
            ? State.price * (1 - s.pct/100)
            : State.price * (1 + s.pct/100);
        return `<button onclick="setSL(${sl})">${s.label} → $${sl.toFixed(2)}</button>`;
    }).join('');
}

function setSL(value) {
    document.getElementById('stopLoss').value = value.toFixed(2);
    updateSummary();
}

function updateSummary() {
    const entry = State.entry === 'MARKET' 
        ? State.price 
        : parseFloat(document.getElementById('entryPrice').value) || State.price;
    
    const capital = parseFloat(document.getElementById('capital').value) || 0;
    const sl = parseFloat(document.getElementById('stopLoss').value) || 0;
    const tp = parseFloat(document.getElementById('takeProfit').value) || 0;
    const leverage = State.leverage;
    
    if (!entry || !capital) return;
    
    // Position size = Capital * Leverage / Entry Price
    const positionValue = capital * leverage;
    const quantity = positionValue / entry;
    
    // Risk calculation
    const riskPerUnit = sl ? Math.abs(entry - sl) : 0;
    const riskAmount = riskPerUnit * quantity;
    const riskPercent = sl ? (riskAmount / capital) * 100 : 0;
    
    // Target 2R
    const target2R = sl 
        ? (State.type === 'LONG' ? entry + riskPerUnit * 2 : entry - riskPerUnit * 2)
        : 0;
    
    const potentialProfit = riskPerUnit * 2 * quantity;
    
    // Update display
    document.getElementById('positionSize').textContent = `$${positionValue.toFixed(2)} (${quantity.toFixed(6)} ${State.coinName})`;
    document.getElementById('summaryEntry').textContent = `$${entry.toFixed(2)}`;
    document.getElementById('riskAmount').textContent = sl ? `$${riskAmount.toFixed(2)}` : '--';
    document.getElementById('riskPercent').textContent = sl ? `${riskPercent.toFixed(1)}%` : '--';
    document.getElementById('target2R').textContent = sl ? `$${target2R.toFixed(2)}` : '--';
    document.getElementById('potentialProfit').textContent = sl ? `$${potentialProfit.toFixed(2)}` : '--';
}

// ==========================================
// BOT CONTROL
// ==========================================

async function startBot() {
    if (!State.connected) {
        toast('Not connected to server!', true);
        return;
    }
    
    const entry = State.entry === 'MARKET' 
        ? State.price 
        : parseFloat(document.getElementById('entryPrice').value);
    
    const capital = parseFloat(document.getElementById('capital').value);
    const sl = parseFloat(document.getElementById('stopLoss').value);
    const tp = parseFloat(document.getElementById('takeProfit').value) || 0;
    const leverage = State.leverage;
    
    // Validation
    if (!capital || capital <= 0) {
        toast('Enter capital amount!', true);
        return;
    }
    
    if (!sl || sl <= 0) {
        toast('Enter stop loss!', true);
        return;
    }
    
    if (State.type === 'LONG' && sl >= entry) {
        toast('SL must be below entry for LONG!', true);
        return;
    }
    
    if (State.type === 'SHORT' && sl <= entry) {
        toast('SL must be above entry for SHORT!', true);
        return;
    }
    
    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Starting...';
    
    try {
        const res = await fetch(`${SERVER}/api/bot/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                coin: State.coin,
                trade_type: State.type,
                entry_type: State.entry,
                entry_price: entry,
                capital: capital,
                stop_loss: sl,
                take_profit: tp,
                leverage: leverage
            })
        });
        
        const result = await res.json();
        
        if (result.success) {
            State.trade = result.trade;
            showMonitor(result.trade);
            toast('Bot started!');
            playSound();
        } else {
            toast(result.error || 'Failed to start', true);
            log(result.error || 'Start failed', 'error');
        }
    } catch (e) {
        toast('Error: ' + e.message, true);
        log('Start error: ' + e.message, 'error');
    }
    
    btn.disabled = false;
    btn.textContent = '🤖 START AUTO TRADING';
}

async function stopBot() {
    if (!State.trade) return;
    if (!confirm('Stop bot and close trade?')) return;
    
    try {
        await fetch(`${SERVER}/api/bot/stop/${State.trade.id}`, { method: 'POST' });
        toast('Trade closed');
        hideMonitor();
    } catch (e) {
        toast('Error closing', true);
    }
}

// ==========================================
// MONITOR
// ==========================================

function showMonitor(trade) {
    document.getElementById('tradeCard').classList.add('hidden');
    document.getElementById('monitorCard').classList.remove('hidden');
    
    document.getElementById('mEntry').textContent = `$${trade.entry_price.toFixed(2)}`;
    document.getElementById('mSL').textContent = `$${trade.current_sl.toFixed(2)}`;
    document.getElementById('mTP').textContent = trade.take_profit 
        ? `$${trade.take_profit.toFixed(2)}` 
        : 'Auto';
    
    // Show trailing levels
    renderLevels(trade.trailing_levels);
}

function hideMonitor() {
    document.getElementById('monitorCard').classList.add('hidden');
    document.getElementById('tradeCard').classList.remove('hidden');
    State.trade = null;
}

function renderLevels(levels) {
    const grid = document.getElementById('levelsGrid');
    grid.innerHTML = levels.map((l, i) => `
        <div class="level-item" id="level-${i}">
            ${l.rr}R → $${l.target_price.toFixed(0)}
        </div>
    `).join('');
}

function onPriceUpdate(data) {
    if (!State.trade || data.trade_id !== State.trade.id) return;
    
    const green = data.current_rr >= 0;
    
    document.getElementById('mPrice').textContent = `$${data.current_price.toLocaleString()}`;
    document.getElementById('mPrice').className = `value ${green ? 'green' : 'red'}`;
    
    document.getElementById('mRR').textContent = `${green ? '+' : ''}${data.current_rr.toFixed(2)}R`;
    document.getElementById('mRR').className = `value ${green ? 'green' : 'red'}`;
    
    document.getElementById('mSL').textContent = `$${data.current_sl.toFixed(2)}`;
    
    document.getElementById('mPnL').textContent = `${data.pnl >= 0 ? '+' : ''}$${data.pnl.toFixed(2)}`;
    document.getElementById('mPnL').className = `value ${data.pnl >= 0 ? 'green' : 'red'}`;
}

function onLevelReached(data) {
    showAlert(
        `🎯 ${data.level.rr}R Target Hit!`,
        `SL trailed to $${data.new_sl.toFixed(2)}\n\n${data.action}`
    );
    
    document.getElementById('actionBox').classList.add('alert');
    document.getElementById('actionText').textContent = data.action;
    
    // Update level UI
    const levelEl = document.querySelector(`#levelsGrid .level-item:nth-child(${Math.floor(data.level.rr * 2)})`);
    if (levelEl) levelEl.classList.add('reached');
    
    playSound();
    vibrate();
}

function onTradeClosed(data) {
    const isTP = data.reason.includes('Take Profit');
    showAlert(
        isTP ? '🎉 Take Profit Hit!' : '⚠️ Stop Loss Hit!',
        `Exit: $${data.exit_price.toFixed(2)}${data.pnl ? `\nProfit: $${data.pnl.toFixed(2)}` : ''}`
    );
    hideMonitor();
}

// ==========================================
// UI HELPERS
// ==========================================

function log(msg, type = 'info') {
    const container = document.getElementById('log');
    const empty = container.querySelector('.empty');
    if (empty) empty.remove();
    
    const time = new Date().toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    const item = document.createElement('div');
    item.className = `log-item ${type}`;
    item.innerHTML = `<span class="time">${time}</span><span class="msg">${msg}</span>`;
    
    container.insertBefore(item, container.firstChild);
    while (container.children.length > 50) container.lastChild.remove();
}

function toast(msg, error = false) {
    const t = document.getElementById('toast');
    document.getElementById('toastMsg').textContent = msg;
    t.classList.remove('hidden', 'error');
    if (error) t.classList.add('error');
    setTimeout(() => t.classList.add('hidden'), 3000);
}

function showAlert(title, msg) {
    document.getElementById('alertTitle').textContent = title;
    document.getElementById('alertMsg').textContent = msg;
    document.getElementById('overlay').classList.remove('hidden');
}

function closeAlert() {
    document.getElementById('overlay').classList.add('hidden');
    document.getElementById('actionBox').classList.remove('alert');
}

function playSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        [0, 0.15, 0.3].forEach(d => {
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.connect(g);
            g.connect(ctx.destination);
            o.frequency.value = 880;
            g.gain.setValueAtTime(0.3, ctx.currentTime + d);
            g.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + d + 0.1);
            o.start(ctx.currentTime + d);
            o.stop(ctx.currentTime + d + 0.1);
        });
    } catch (e) {}
}

function vibrate() {
    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
}