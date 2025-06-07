// Main JavaScript file for Trading Journal

// Global variables
let trades = [];
let statistics = {};
let currentWeekOffset = 0;

// DOM Elements
const tradesTableBody = document.getElementById('tradesTableBody');
const totalTradesElement = document.getElementById('totalTrades');
const winRateElement = document.getElementById('winRate');
const profitFactorElement = document.getElementById('profitFactor');
const expectancyElement = document.getElementById('expectancy');
const addTradeForm = document.getElementById('addTradeForm');
const saveTradeButton = document.getElementById('saveTrade');

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    loadWeeklyTrades();
    loadStatistics();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    saveTradeButton.addEventListener('click', saveTrade);
}

// Load trades from the API
async function loadTrades() {
    try {
        const response = await fetch('/api/trades');
        trades = await response.json();
        displayTrades(trades);
    } catch (error) {
        console.error('Error loading trades:', error);
        showAlert('Error loading trades. Please try again.', 'danger');
    }
}

// Load statistics from the API
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        statistics = await response.json();
        updateDashboard();
    } catch (error) {
        console.error('Error loading statistics:', error);
        showAlert('Error loading statistics. Please try again.', 'danger');
    }
}

// Load weekly trades
async function loadWeeklyTrades() {
    try {
        const response = await fetch(`/api/trades/weekly?week_offset=${currentWeekOffset}`);
        const data = await response.json();
        displayWeeklyTrades(data);
    } catch (error) {
        console.error('Error loading weekly trades:', error);
        showAlert('Error loading trades. Please try again.', 'danger');
    }
}

// Display trades grouped by date
function displayTrades(trades) {
    const tradesList = document.getElementById('tradesList');
    tradesList.innerHTML = '';

    // Group trades by date
    const tradesByDate = trades.reduce((groups, trade) => {
        const date = new Date(trade.entry_datetime).toLocaleDateString();
        if (!groups[date]) {
            groups[date] = [];
        }
        groups[date].push(trade);
        return groups;
    }, {});

    // Sort dates in descending order
    const sortedDates = Object.keys(tradesByDate).sort((a, b) => new Date(b) - new Date(a));

    // Create trade cards for each date
    sortedDates.forEach(date => {
        const dateGroup = document.createElement('div');
        dateGroup.className = 'trade-day';

        const dateHeader = document.createElement('div');
        dateHeader.className = 'trade-day-header';
        dateHeader.textContent = date;
        dateGroup.appendChild(dateHeader);

        tradesByDate[date].forEach(trade => {
            const tradeCard = createTradeCard(trade);
            dateGroup.appendChild(tradeCard);
        });

        tradesList.appendChild(dateGroup);
    });
}

// Create a trade card
function createTradeCard(trade) {
    const card = document.createElement('div');
    card.className = `trade-card ${trade.status.toLowerCase()}`;
    card.onclick = () => showTradeDetail(trade);

    const cardBody = document.createElement('div');
    cardBody.className = 'card-body';

    const row = document.createElement('div');
    row.className = 'row';

    // Trade information
    const infoCol = document.createElement('div');
    infoCol.className = 'col-md-8';
    infoCol.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <h6 class="mb-1">${trade.instrument}</h6>
                <div class="text-muted small">
                    ${new Date(trade.entry_datetime).toLocaleTimeString()} - 
                    ${new Date(trade.exit_datetime).toLocaleTimeString()}
                </div>
            </div>
            <span class="trade-status ${trade.status.toLowerCase()}">${trade.status}</span>
        </div>
        <div class="mt-2">
            <div class="d-flex gap-3">
                <div>
                    <small class="text-muted">Entry</small>
                    <div>${trade.entry_price}</div>
                </div>
                <div>
                    <small class="text-muted">Exit</small>
                    <div>${trade.exit_price}</div>
                </div>
                <div>
                    <small class="text-muted">P/L</small>
                    <div class="${trade.status === 'WIN' ? 'text-success' : trade.status === 'LOSS' ? 'text-danger' : 'text-warning'}">
                        ${calculatePL(trade)}
                    </div>
                </div>
                <div>
                    <small class="text-muted">R</small>
                    <div class="trade-r ${getRClass(trade)}">${calculateR(trade)}</div>
                </div>
            </div>
        </div>
    `;

    // Trade actions
    const actionsCol = document.createElement('div');
    actionsCol.className = 'col-md-4';
    actionsCol.innerHTML = `
        <div class="trade-actions justify-content-end">
            <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); editTrade(${trade.id})">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteTrade(${trade.id})">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `;

    row.appendChild(infoCol);
    row.appendChild(actionsCol);
    cardBody.appendChild(row);
    card.appendChild(cardBody);

    return card;
}

// Show trade detail
function showTradeDetail(trade) {
    const tradeDetail = document.getElementById('tradeDetail');
    tradeDetail.style.display = 'block';

    // Display entry images
    const entryImages = document.getElementById('entryImages');
    entryImages.innerHTML = '';
    if (trade.entry_image) {
        const imageDiv = document.createElement('div');
        imageDiv.className = 'trade-image';
        imageDiv.innerHTML = `
            <img src="/uploads/${trade.entry_image}" alt="Entry setup">
            <div class="trade-image-description">${trade.entry_image_description || ''}</div>
        `;
        entryImages.appendChild(imageDiv);
    }

    // Display exit images
    const exitImages = document.getElementById('exitImages');
    exitImages.innerHTML = '';
    if (trade.exit_image) {
        const imageDiv = document.createElement('div');
        imageDiv.className = 'trade-image';
        imageDiv.innerHTML = `
            <img src="/uploads/${trade.exit_image}" alt="Exit result">
            <div class="trade-image-description">${trade.exit_image_description || ''}</div>
        `;
        exitImages.appendChild(imageDiv);
    }

    // Display trade information
    const tradeInfo = document.getElementById('tradeInfo');
    tradeInfo.innerHTML = `
        <table class="trade-info-table">
            <tr>
                <th>Instrument</th>
                <td>${trade.instrument}</td>
            </tr>
            <tr>
                <th>Entry Date/Time</th>
                <td>${new Date(trade.entry_datetime).toLocaleString()}</td>
            </tr>
            <tr>
                <th>Exit Date/Time</th>
                <td>${new Date(trade.exit_datetime).toLocaleString()}</td>
            </tr>
            <tr>
                <th>Order Type</th>
                <td>${trade.order_type}</td>
            </tr>
            <tr>
                <th>Entry Price</th>
                <td>${trade.entry_price}</td>
            </tr>
            <tr>
                <th>Exit Price</th>
                <td>${trade.exit_price}</td>
            </tr>
            <tr>
                <th>Initial Stop Loss</th>
                <td>${trade.initial_stop_loss}</td>
            </tr>
            <tr>
                <th>Initial Take Profit</th>
                <td>${trade.initial_take_profit}</td>
            </tr>
            <tr>
                <th>Position Size</th>
                <td>${trade.position_size}</td>
            </tr>
            <tr>
                <th>Status</th>
                <td><span class="trade-status ${trade.status.toLowerCase()}">${trade.status}</span></td>
            </tr>
            <tr>
                <th>P/L</th>
                <td class="${trade.status === 'WIN' ? 'text-success' : trade.status === 'LOSS' ? 'text-danger' : 'text-warning'}">
                    ${calculatePL(trade)}
                </td>
            </tr>
            <tr>
                <th>R</th>
                <td class="trade-r ${getRClass(trade)}">${calculateR(trade)}</td>
            </tr>
            <tr>
                <th>Rationale</th>
                <td>${trade.rationale || '-'}</td>
            </tr>
            <tr>
                <th>Review</th>
                <td>${trade.review || '-'}</td>
            </tr>
            <tr>
                <th>Emotions</th>
                <td>${trade.emotions || '-'}</td>
            </tr>
            <tr>
                <th>Tags</th>
                <td>
                    <div class="trade-tags">
                        ${(trade.tags || '').split(',').map(tag => `
                            <span class="trade-tag">${tag.trim()}</span>
                        `).join('')}
                    </div>
                </td>
            </tr>
        </table>
    `;

    // Scroll to trade detail
    tradeDetail.scrollIntoView({ behavior: 'smooth' });
}

// Calculate P/L
function calculatePL(trade) {
    const multiplier = trade.order_type === 'BUY' ? 1 : -1;
    const pl = (trade.exit_price - trade.entry_price) * trade.position_size * multiplier;
    return pl.toFixed(2);
}

// Calculate R
function calculateR(trade) {
    const multiplier = trade.order_type === 'BUY' ? 1 : -1;
    const pl = (trade.exit_price - trade.entry_price) * trade.position_size * multiplier;
    const risk = Math.abs(trade.entry_price - trade.initial_stop_loss) * trade.position_size;
    return (pl / risk).toFixed(2);
}

// Get R class for styling
function getRClass(trade) {
    const r = parseFloat(calculateR(trade));
    if (r > 0) return 'positive';
    if (r < 0) return 'negative';
    return 'neutral';
}

// Delete trade
async function deleteTrade(tradeId) {
    if (!confirm('Are you sure you want to delete this trade?')) return;

    try {
        const response = await fetch(`/api/trades/${tradeId}`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            // Remove trade from the list
            trades = trades.filter(t => t.id !== tradeId);
            // Update UI
            await loadWeeklyTrades();
            await loadStatistics();
            // Hide trade detail if it's showing the deleted trade
            const tradeDetail = document.getElementById('tradeDetail');
            if (tradeDetail.style.display === 'block') {
                tradeDetail.style.display = 'none';
            }
            showAlert('Trade deleted successfully!', 'success');
        } else {
            throw new Error(data.error || 'Failed to delete trade');
        }
    } catch (error) {
        console.error('Error deleting trade:', error);
        showAlert(error.message || 'Error deleting trade. Please try again.', 'danger');
    }
}

// Edit trade
async function editTrade(tradeId) {
    const trade = trades.find(t => t.id === tradeId);
    if (!trade) return;

    // Populate form with trade data
    Object.keys(trade).forEach(key => {
        const input = addTradeForm.elements[key];
        if (input) {
            input.value = trade[key];
        }
    });

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('addTradeModal'));
    modal.show();
}

// Update dashboard statistics
function updateDashboard() {
    totalTradesElement.textContent = statistics.total_trades;
    winRateElement.textContent = `${(statistics.win_rate * 100).toFixed(1)}%`;
    profitFactorElement.textContent = statistics.profit_factor.toFixed(2);
    expectancyElement.textContent = formatNumber(statistics.expectancy);
}

// Save trade
async function saveTrade() {
    const formData = new FormData(addTradeForm);
    const tradeData = {
        entry_datetime: formData.get('entry_datetime'),
        exit_datetime: formData.get('exit_datetime'),
        instrument: formData.get('instrument'),
        order_type: formData.get('order_type'),
        entry_price: parseFloat(formData.get('entry_price')),
        exit_price: parseFloat(formData.get('exit_price')),
        initial_stop_loss: parseFloat(formData.get('initial_stop_loss')),
        initial_take_profit: parseFloat(formData.get('initial_take_profit')),
        position_size: parseFloat(formData.get('position_size')),
        status: formData.get('status'),
        net_profit: parseFloat(formData.get('net_profit')),
        r_value: parseFloat(formData.get('r_value')),
        rationale: formData.get('rationale'),
        review: formData.get('review'),
        emotions: formData.get('emotions'),
        tags: formData.get('tags')
    };

    try {
        // First, save the trade
        const response = await fetch('/api/trades', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(tradeData),
        });

        if (response.ok) {
            const newTrade = await response.json();

            // Upload entry image if exists
            const entryImage = formData.get('entry_image');
            if (entryImage && entryImage.size > 0) {
                const entryImageData = new FormData();
                entryImageData.append('image', entryImage);
                entryImageData.append('image_type', 'ENTRY');
                entryImageData.append('description', formData.get('entry_image_description'));

                await fetch(`/api/trades/${newTrade.id}/images`, {
                    method: 'POST',
                    body: entryImageData
                });
            }

            // Upload exit image if exists
            const exitImage = formData.get('exit_image');
            if (exitImage && exitImage.size > 0) {
                const exitImageData = new FormData();
                exitImageData.append('image', exitImage);
                exitImageData.append('image_type', 'EXIT');
                exitImageData.append('description', formData.get('exit_image_description'));

                await fetch(`/api/trades/${newTrade.id}/images`, {
                    method: 'POST',
                    body: exitImageData
                });
            }

            // Add new trade to the trades array
            trades.unshift(newTrade);

            // Reload weekly trades to show the new trade
            await loadWeeklyTrades();

            // Update statistics
            await loadStatistics();

            // Close modal and show success message
            closeModal('addTradeModal');
            showAlert('Trade saved successfully!', 'success');
        } else {
            throw new Error('Failed to save trade');
        }
    } catch (error) {
        console.error('Error saving trade:', error);
        showAlert(error.message || 'Error saving trade. Please try again.', 'danger');
    }
}

// Utility functions
function formatDateTime(dateTimeStr) {
    const date = new Date(dateTimeStr);
    return date.toLocaleString();
}

function formatNumber(number) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 5,
    }).format(number);
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.querySelector('.container-fluid').insertAdjacentElement('afterbegin', alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function closeModal(modalId) {
    const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
    if (modal) {
        modal.hide();
    }
    addTradeForm.reset();
}

// Display weekly trades
function displayWeeklyTrades(data) {
    const weeklyTrades = document.getElementById('weeklyTrades');
    const weekRange = document.getElementById('weekRange');

    // Update week range display
    weekRange.textContent = `${formatDate(data.week_start)} - ${formatDate(data.week_end)}`;

    // Create weekly view
    let html = `
        <div class="table-responsive">
            <table class="table table-bordered weekly-trades-table">
                <thead>
                    <tr>
                        <th style="width: 150px;">Date</th>
                        <th>Trades</th>
                    </tr>
                </thead>
                <tbody>
    `;

    data.days.forEach(day => {
        html += `
            <tr>
                <td class="day-header">
                    <div class="d-flex flex-column">
                        <span class="weekday">${new Date(day.date).toLocaleDateString('en-US', { weekday: 'long' })}</span>
                        <span class="date">${new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                    </div>
                </td>
                <td>
                    ${day.trades.length === 0 ?
                '<div class="no-trades">No trades for this day</div>' :
                '<div class="trades-list">' +
                day.trades.map(trade => `
                            <div class="trade-item" data-trade-id="${trade.id}">
                                <div class="trade-time">${new Date(trade.entry_datetime).toLocaleTimeString()}</div>
                                <div class="trade-info">
                                    <span class="trade-instrument">${trade.instrument}</span>
                                    <span class="trade-type">${trade.order_type}</span>
                                    <span class="trade-status ${trade.status.toLowerCase()}">${trade.status}</span>
                                    <span class="trade-pl ${trade.status === 'WIN' ? 'text-success' : trade.status === 'LOSS' ? 'text-danger' : 'text-warning'}">
                                        ${calculatePL(trade)}
                                    </span>
                                </div>
                            </div>
                        `).join('') +
                '</div>'
            }
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    weeklyTrades.innerHTML = html;

    // Add click event listeners to trade items
    document.querySelectorAll('.trade-item').forEach(item => {
        item.addEventListener('click', () => {
            const tradeId = parseInt(item.dataset.tradeId);
            const trade = trades.find(t => t.id === tradeId);
            if (trade) {
                showTradeDetail(trade);
            }
        });
    });
}

// Format date for display
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Event listeners for week navigation
document.getElementById('prevWeek').addEventListener('click', () => {
    currentWeekOffset++;
    loadWeeklyTrades();
});

document.getElementById('nextWeek').addEventListener('click', () => {
    if (currentWeekOffset > 0) {
        currentWeekOffset--;
        loadWeeklyTrades();
    }
}); 