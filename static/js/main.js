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
    setupEventListeners();
    loadWeeklyTrades();
    loadStatistics();
});

// Event Listeners
function setupEventListeners() {
    saveTradeButton.addEventListener('click', saveTrade);

    // --- Start of Week Navigation Logic ---
    const prevWeekBtn = document.getElementById('prevWeek');
    const nextWeekBtn = document.getElementById('nextWeek');
    const todayWeekBtn = document.getElementById('todayWeek');

    prevWeekBtn.addEventListener('click', () => {
        currentWeekOffset++;
        loadWeeklyTrades();
    });

    nextWeekBtn.addEventListener('click', () => {
        if (currentWeekOffset > 0) {
            currentWeekOffset--;
            loadWeeklyTrades();
        }
    });

    const calendar = flatpickr(todayWeekBtn, {
        inline: false, // Show as a dropdown
        onChange: function (selectedDates, dateStr, instance) {
            const selectedDate = selectedDates[0];

            // Helper to get the start of the week (Monday) for a given date
            const getStartOfWeek = (date) => {
                const d = new Date(date);
                // Adjust for week starting on Monday
                const day = d.getDay();
                const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
                const monday = new Date(d.setDate(diff));
                monday.setHours(0, 0, 0, 0);
                return monday;
            };

            const startOfCurrentWeek = getStartOfWeek(new Date());
            const startOfSelectedWeek = getStartOfWeek(selectedDate);

            // Calculate the difference in milliseconds
            const diffTime = startOfCurrentWeek.getTime() - startOfSelectedWeek.getTime();

            // Calculate the difference in weeks and round it to the nearest whole number
            const diffWeeks = Math.round(diffTime / (1000 * 60 * 60 * 24 * 7));

            currentWeekOffset = diffWeeks;
            loadWeeklyTrades();
        }
    });

    todayWeekBtn.addEventListener('click', (e) => {
        e.preventDefault();
        calendar.open();
    });
    // --- End of Week Navigation Logic ---

    // --- Net Profit Calculation Logic ---
    const tradeForm = document.getElementById('addTradeForm');
    const fieldsForCalculation = ['entry_price', 'exit_price', 'position_size', 'order_type'];
    fieldsForCalculation.forEach(fieldName => {
        const input = tradeForm.querySelector(`[name="${fieldName}"]`);
        if (input) {
            input.addEventListener('input', calculateNetProfit);
        }
    });

    // --- Modal Reset Logic ---
    const addTradeModalEl = document.getElementById('addTradeModal');
    addTradeModalEl.addEventListener('hidden.bs.modal', () => {
        tradeForm.reset();
        delete tradeForm.dataset.editId;
        document.querySelector('#addTradeModal .modal-title').textContent = 'Add New Trade';
    });

    // Close trade detail view
    const closeBtn = document.getElementById('closeTradeDetail');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            const detailView = document.getElementById('tradeDetail');
            if (detailView) {
                detailView.style.display = 'none';
            }
        });
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

        // Flatten trades from all days into the global trades array
        trades = data.days.flatMap(day => day.trades);

        displayWeeklyTrades(data);

        // Disable next week button if viewing current week or future
        document.getElementById('nextWeek').disabled = currentWeekOffset <= 0;

    } catch (error) {
        console.error('Error loading weekly trades:', error);
        showAlert('Error loading trades. Please try again.', 'danger');
    }
}

// Display weekly trades
function displayWeeklyTrades(data) {
    const weeklyTradesContainer = document.getElementById('weeklyTrades');
    const weekRange = document.getElementById('weekRange');

    if (!weeklyTradesContainer || !weekRange) {
        console.error('UI elements for weekly display not found!');
        return;
    }

    // Update week range display
    weekRange.textContent = `${formatDate(data.week_start)} - ${formatDate(data.week_end)}`;

    // Create weekly view table
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
                                <div class="trade-item-main">
                                    <div class="trade-time">${new Date(trade.entry_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                                    <div class="trade-info" onclick="showTradeDetail(trades.find(t => t.id === ${trade.id}))">
                                        <span class="trade-instrument">${trade.instrument}</span>
                                        <span class="trade-type">${trade.order_type}</span>
                                        <span class="trade-status ${trade.status.toLowerCase()}">${trade.status}</span>
                                        <span class="trade-pl ${trade.net_profit > 0 ? 'text-success' : trade.net_profit < 0 ? 'text-danger' : ''}">
                                            ${Number(trade.net_profit).toFixed(2)}
                                        </span>
                                    </div>
                                </div>
                                <div class="trade-actions">
                                    <button class="btn btn-sm btn-outline-secondary" onclick="editTrade(${trade.id})">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTrade(${trade.id})">
                                        <i class="bi bi-trash"></i>
                                    </button>
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

    weeklyTradesContainer.innerHTML = html;

    // Add click event listeners to trade items for detail view
    document.querySelectorAll('.trade-item .trade-info').forEach(item => {
        item.addEventListener('click', () => {
            const tradeId = parseInt(item.closest('.trade-item').dataset.tradeId);
            const trade = trades.find(t => t.id === tradeId);
            if (trade) {
                showTradeDetail(trade);
            } else {
                console.error(`Trade with ID ${tradeId} not found in global list.`);
            }
        });
    });
}

// Show trade detail
function showTradeDetail(trade) {
    const detailView = document.getElementById('tradeDetail');
    if (!detailView) {
        console.error('Trade detail view element not found!');
        return;
    }

    // Populate fields
    document.getElementById('tradeInstrument').textContent = trade.instrument || 'N/A';
    document.getElementById('tradeOrderType').textContent = trade.order_type || 'N/A';
    document.getElementById('tradeEntryDateTime').textContent = trade.entry_datetime ? new Date(trade.entry_datetime).toLocaleString() : 'N/A';
    document.getElementById('tradeExitDateTime').textContent = trade.exit_datetime ? new Date(trade.exit_datetime).toLocaleString() : 'N/A';
    document.getElementById('tradeEntryPrice').textContent = trade.entry_price || 'N/A';
    document.getElementById('tradeExitPrice').textContent = trade.exit_price || 'N/A';
    document.getElementById('tradeStopLoss').textContent = trade.initial_stop_loss || 'N/A';
    document.getElementById('tradeTakeProfit').textContent = trade.initial_take_profit || 'N/A';
    document.getElementById('tradePositionSize').textContent = trade.position_size || 'N/A';
    document.getElementById('tradeStatus').textContent = trade.status || 'N/A';
    document.getElementById('tradeRationale').textContent = trade.rationale || 'No rationale provided.';
    document.getElementById('tradeReview').textContent = trade.review || 'No review provided.';
    document.getElementById('tradeEmotions').textContent = trade.emotions || 'No emotions recorded.';
    document.getElementById('tradeTags').textContent = trade.tags || 'No tags.';

    // Render images
    const entryImagesDiv = document.getElementById('entryImages');
    const exitImagesDiv = document.getElementById('exitImages');
    entryImagesDiv.innerHTML = '';
    exitImagesDiv.innerHTML = '';

    if (trade.images && trade.images.length > 0) {
        trade.images.forEach(img => {
            const container = img.image_type === 'ENTRY' ? entryImagesDiv : exitImagesDiv;
            if (container) {
                container.innerHTML += `
                    <div class="trade-image-item">
                        <img src="/uploads/${img.image_path}" class="img-fluid" alt="Trade image">
                        <p class="small text-muted mt-1">${img.description || ''}</p>
                    </div>
                `;
            }
        });
    }

    detailView.style.display = 'block';
    detailView.scrollIntoView({ behavior: 'smooth' });
}

// Calculate P/L
function calculatePL(trade) {
    // This calculation is now based on net_profit from the server
    return Number(trade.net_profit).toFixed(2);
}

// Calculate R
function calculateR(trade) {
    // This calculation is now based on r_value from the server
    return Number(trade.r_value).toFixed(2);
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
            method: 'DELETE'
        });

        if (response.ok) {
            // Hide trade detail if it's showing the deleted trade
            const tradeDetail = document.getElementById('tradeDetail');
            if (tradeDetail.style.display === 'block') {
                // A bit of a hack: check if the detail view is for the deleted trade
                const displayedInstrument = document.getElementById('tradeInstrument').textContent;
                const deletedTrade = trades.find(t => t.id === tradeId);
                if (deletedTrade && displayedInstrument === deletedTrade.instrument) {
                    tradeDetail.style.display = 'none';
                }
            }

            showAlert('Trade deleted successfully!', 'success');

            // Reload data without full page refresh
            await loadWeeklyTrades();
            await loadStatistics();

        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to delete trade');
        }
    } catch (error) {
        console.error('Error deleting trade:', error);
        showAlert(error.message || 'Error deleting trade. Please try again.', 'danger');
    }
}

// Edit trade
async function editTrade(tradeId) {
    const trade = trades.find(t => t.id === tradeId);
    if (!trade) {
        showAlert('Could not find trade data to edit.', 'danger');
        return;
    }

    const form = document.getElementById('addTradeForm');
    form.dataset.editId = trade.id;

    // Populate form
    document.querySelector('#addTradeModal .modal-title').textContent = `Edit Trade #${trade.id}`;
    form.querySelector('[name="entry_datetime"]').value = trade.entry_datetime ? trade.entry_datetime.slice(0, 16) : '';
    form.querySelector('[name="exit_datetime"]').value = trade.exit_datetime ? trade.exit_datetime.slice(0, 16) : '';
    form.querySelector('[name="instrument"]').value = trade.instrument || '';
    form.querySelector('[name="order_type"]').value = trade.order_type || 'BUY';
    form.querySelector('[name="entry_price"]').value = trade.entry_price || '';
    form.querySelector('[name="exit_price"]').value = trade.exit_price || '';
    form.querySelector('[name="initial_stop_loss"]').value = trade.initial_stop_loss || '';
    form.querySelector('[name="initial_take_profit"]').value = trade.initial_take_profit || '';
    form.querySelector('[name="position_size"]').value = trade.position_size || '';
    form.querySelector('[name="status"]').value = trade.status || 'WIN';
    form.querySelector('[name="rationale"]').value = trade.rationale || '';
    form.querySelector('[name="review"]').value = trade.review || '';
    form.querySelector('[name="emotions"]').value = trade.emotions || '';
    form.querySelector('[name="tags"]').value = trade.tags || '';

    // Calculated fields
    form.querySelector('[name="net_profit"]').value = trade.net_profit || '';
    form.querySelector('[name="r_value"]').value = trade.r_value || '';

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
    const saveButton = document.getElementById('saveTrade');
    saveButton.disabled = true;

    const formData = new FormData(addTradeForm);
    const tradeId = addTradeForm.dataset.editId;

    let url = '/api/trades';

    if (tradeId) {
        url = `/api/trades/update/${tradeId}`;
    }

    try {
        const response = await fetch(url, {
            method: 'POST', // Always POST to handle FormData
            body: formData,
        });

        if (response.ok) {
            showAlert('Trade saved successfully!', 'success');

            // Manually blur the active element (the save button) to remove focus.
            // This resolves the aria-hidden accessibility warning.
            if (document.activeElement) {
                document.activeElement.blur();
            }

            const modal = bootstrap.Modal.getInstance(document.getElementById('addTradeModal'));
            if (modal) {
                modal.hide();
            }

            addTradeForm.reset();
            delete addTradeForm.dataset.editId;
            document.querySelector('#addTradeModal .modal-title').textContent = 'Add New Trade';

            await loadWeeklyTrades();
            await loadStatistics();

        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to save trade');
        }
    } catch (error) {
        console.error('Error saving trade:', error);
        showAlert(error.message || 'Error saving trade. Please try again.', 'danger');
    } finally {
        // Re-enable the button whether the save succeeded or failed
        saveButton.disabled = false;
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

// Format date for display
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });
}

function calculateNetProfit() {
    const form = document.getElementById('addTradeForm');
    const entryPriceInput = form.querySelector('[name="entry_price"]');
    const entryPrice = parseFloat(entryPriceInput.value);
    const exitPrice = parseFloat(form.querySelector('[name="exit_price"]').value);
    const positionSize = parseFloat(form.querySelector('[name="position_size"]').value);
    const orderType = form.querySelector('[name="order_type"]').value;
    const netProfitInput = form.querySelector('[name="net_profit"]');

    if (isNaN(entryPrice) || isNaN(exitPrice) || isNaN(positionSize) || !orderType || !entryPriceInput.value) {
        netProfitInput.value = '';
        return;
    }

    // Dynamically determine pip size by inspecting the entry price's decimal places.
    const getPipSize = (priceString) => {
        if (priceString.includes('.')) {
            const decimalPlaces = priceString.split('.')[1].length;
            // Instruments like JPY pairs typically have 2 or 3 decimal places.
            if (decimalPlaces <= 3) {
                return 0.01;
            }
        }
        // Most other pairs have 4 or 5 decimal places (the 5th being a pipette).
        return 0.0001;
    };

    const pipSize = getPipSize(entryPriceInput.value);

    // The value of 1 pip for 1 standard lot (100,000 units) for a USD-quoted pair.
    const pipValuePerStandardLot = 10;

    // Calculate the difference in pips
    let pips = 0;
    if (orderType.toUpperCase() === 'BUY') {
        pips = (exitPrice - entryPrice) / pipSize;
    } else if (orderType.toUpperCase() === 'SELL') {
        pips = (entryPrice - exitPrice) / pipSize;
    }

    // Calculate net profit using the standard formula
    const profit = pips * pipValuePerStandardLot * positionSize;

    netProfitInput.value = profit.toFixed(2);
} 