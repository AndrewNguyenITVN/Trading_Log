from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import json
from werkzeug.utils import secure_filename
import uuid
import webview
import threading

app = Flask(__name__)
CORS(app)

# --- Configuration for Portability ---
# Use the instance folder for all user-generated data (database, uploads).
# This is the standard Flask way and makes the app portable.
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

app.config['INSTANCE_PATH'] = instance_path
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(instance_path, 'trading_journal.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(instance_path, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
from models import db

db.init_app(app)

# Import models
from models.trade import Trade
from models.trade_image import TradeImage

# Create database tables
with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/trades', methods=['GET'])
def get_trades():
    trades = Trade.query.order_by(Trade.entry_datetime.desc()).all()
    results = []
    for trade in trades:
        try:
            results.append(trade.to_dict())
        except Exception as e:
            app.logger.error(f"Error serializing trade {trade.id}: {e}")
            # Skip trades that cause errors, possibly due to old data
            continue
    return jsonify(results)

@app.route('/api/trades', methods=['POST'])
def create_trade():
    try:
        data = request.form.to_dict()
        
        # Enforce required fields based on user specification
        required_fields = [
            'entry_datetime', 'exit_datetime', 'instrument', 'order_type', 
            'entry_price', 'exit_price', 'initial_stop_loss', 
            'initial_take_profit', 'position_size', 'status'
        ]
        
        missing_or_empty_fields = [field for field in required_fields if not data.get(field)]
        if missing_or_empty_fields:
            error_message = f'Missing or empty required fields: {", ".join(missing_or_empty_fields)}'
            return jsonify({'error': error_message}), 400

        trade = Trade(
            entry_datetime=datetime.fromisoformat(data['entry_datetime']),
            exit_datetime=datetime.fromisoformat(data['exit_datetime']),
            instrument=data['instrument'],
            order_type=data['order_type'],
            entry_price=float(data['entry_price']),
            exit_price=float(data['exit_price']),
            initial_stop_loss=float(data['initial_stop_loss']),
            initial_take_profit=float(data['initial_take_profit']),
            position_size=float(data['position_size']),
            status=data['status'],
            net_profit=float(data.get('net_profit') or 0),
            r_value=float(data.get('r_value') or 0),
            rationale=data.get('rationale', ''),
            review=data.get('review', ''),
            emotions=data.get('emotions', ''),
            tags=data.get('tags', '')
        )
        db.session.add(trade)
        db.session.flush()  # Flush to get the trade.id for image association

        # Handle image uploads
        if 'entry_image' in request.files:
            upload_image_for_trade(request.files['entry_image'], trade.id, 'ENTRY', data.get('entry_image_description'))
        
        if 'exit_image' in request.files:
            upload_image_for_trade(request.files['exit_image'], trade.id, 'EXIT', data.get('exit_image_description'))

        db.session.commit()
        return jsonify(trade.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating trade: {e}")
        # Provide a more specific error message if possible
        if 'invalid isoformat' in str(e):
            return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DDTHH:MM.'}), 400
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@app.route('/api/trades/<int:trade_id>', methods=['GET'])
def get_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    return jsonify(trade.to_dict())

@app.route('/api/trades/update/<int:trade_id>', methods=['POST'])
def update_trade_form(trade_id):
    try:
        trade = Trade.query.get_or_404(trade_id)
        data = request.form.to_dict()
        
        # Update trade fields from form data
        trade.entry_datetime = datetime.fromisoformat(data.get('entry_datetime')) if data.get('entry_datetime') else trade.entry_datetime
        trade.exit_datetime = datetime.fromisoformat(data.get('exit_datetime')) if data.get('exit_datetime') else trade.exit_datetime
        trade.instrument = data.get('instrument', trade.instrument)
        trade.order_type = data.get('order_type', trade.order_type)
        trade.entry_price = float(data.get('entry_price', trade.entry_price))
        trade.exit_price = float(data.get('exit_price', trade.exit_price))
        trade.initial_stop_loss = float(data.get('initial_stop_loss') or trade.initial_stop_loss)
        trade.initial_take_profit = float(data.get('initial_take_profit') or trade.initial_take_profit)
        trade.position_size = float(data.get('position_size') or trade.position_size)
        trade.status = data.get('status', trade.status)
        trade.net_profit = float(data.get('net_profit') or trade.net_profit)
        trade.r_value = float(data.get('r_value') or trade.r_value)
        trade.rationale = data.get('rationale', trade.rationale)
        trade.review = data.get('review', trade.review)
        trade.emotions = data.get('emotions', trade.emotions)
        trade.tags = data.get('tags', trade.tags)
        trade.updated_at = datetime.utcnow()
        
        # Handle image uploads - re-upload replaces old ones
        if 'entry_image' in request.files and request.files['entry_image'].filename != '':
             upload_image_for_trade(request.files['entry_image'], trade.id, 'ENTRY', data.get('entry_image_description'), overwrite=True)
        if 'exit_image' in request.files and request.files['exit_image'].filename != '':
             upload_image_for_trade(request.files['exit_image'], trade.id, 'EXIT', data.get('exit_image_description'), overwrite=True)

        db.session.commit()
        return jsonify(trade.to_dict())
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating trade {trade_id}: {e}")
        if 'invalid isoformat' in str(e):
            return jsonify({'error': 'Invalid date format for update. Please use YYYY-MM-DDTHH:MM.'}), 400
        return jsonify({'error': f'An unexpected error occurred during update: {e}'}), 500

@app.route('/api/trades/<int:trade_id>', methods=['PUT'])
def update_trade(trade_id):
    try:
        trade = Trade.query.get_or_404(trade_id)
        data = request.get_json()
        
        # Update trade fields from JSON data
        trade.entry_datetime = datetime.fromisoformat(data['entry_datetime'])
        trade.exit_datetime = datetime.fromisoformat(data['exit_datetime'])
        trade.instrument = data['instrument']
        trade.order_type = data['order_type']
        trade.entry_price = float(data['entry_price'])
        trade.exit_price = float(data['exit_price'])
        trade.initial_stop_loss = float(data['initial_stop_loss'])
        trade.initial_take_profit = float(data['initial_take_profit'])
        trade.position_size = float(data['position_size'])
        trade.status = data['status']
        trade.net_profit = float(data['net_profit'])
        trade.r_value = float(data['r_value'])
        trade.rationale = data['rationale']
        trade.review = data['review']
        trade.emotions = data['emotions']
        trade.tags = data['tags']
        trade.updated_at = datetime.utcnow()
        
        # Note: Image uploads are handled separately via POST to /api/trades/<id>/images
        # This keeps the PUT request clean for JSON data.

        db.session.commit()
        return jsonify(trade.to_dict())
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating trade {trade_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trades/<int:trade_id>', methods=['DELETE'])
def delete_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    
    # Delete associated image files and records
    for image in trade.images:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            app.logger.error(f"Error deleting image file {image.image_path}: {e}")
        db.session.delete(image)

    db.session.delete(trade)
    db.session.commit()
    return '', 204

def upload_image_for_trade(file, trade_id, image_type, description, overwrite=False):
    if file and allowed_file(file.filename):
        # If overwriting, delete the old image of the same type
        if overwrite:
            old_image = TradeImage.query.filter_by(trade_id=trade_id, image_type=image_type).first()
            if old_image:
                try:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image.image_path)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                except Exception as e:
                    app.logger.error(f"Error deleting old image file {old_image.image_path}: {e}")
                db.session.delete(old_image)

        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        image = TradeImage(
            trade_id=trade_id,
            image_path=unique_filename,
            image_type=image_type,
            description=description
        )
        db.session.add(image)

@app.route('/api/trades/<int:trade_id>/images', methods=['POST'])
def upload_trade_image(trade_id):
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        image_type = request.form.get('image_type', 'ENTRY')
        description = request.form.get('description', '')

        # Find and delete the old image of the same type, if it exists
        old_image = TradeImage.query.filter_by(trade_id=trade_id, image_type=image_type).first()
        if old_image:
            try:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image.image_path)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            except Exception as e:
                app.logger.error(f"Error deleting old image file {old_image.image_path}: {e}")
            db.session.delete(old_image)

        # Save the new image
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Create a new database record for the new image
        new_image = TradeImage(
            trade_id=trade_id,
            image_path=unique_filename,
            image_type=image_type,
            description=description
        )
        db.session.add(new_image)
        db.session.commit()
        
        return jsonify(new_image.to_dict()), 201
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/trades/<int:trade_id>/images', methods=['GET'])
def get_trade_images(trade_id):
    images = TradeImage.query.filter_by(trade_id=trade_id).all()
    return jsonify([image.to_dict() for image in images])

@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    trades = Trade.query.all()
    total_trades = len(trades)

    if not trades:
        return jsonify({
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'expectancy': 0
        })

    # Base calculations on objective net_profit, not user-selected status
    winning_trades = [t for t in trades if t.net_profit > 0]
    losing_trades = [t for t in trades if t.net_profit < 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    
    # Win Rate is based on all trades taken
    win_rate = win_count / total_trades if total_trades > 0 else 0
    loss_rate = loss_count / total_trades if total_trades > 0 else 0

    gross_profit = sum(t.net_profit for t in winning_trades)
    gross_loss = abs(sum(t.net_profit for t in losing_trades))
    
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    avg_win = gross_profit / win_count if win_count > 0 else 0
    avg_loss = gross_loss / loss_count if loss_count > 0 else 0
    
    expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

    return jsonify({
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'expectancy': expectancy
    })

@app.route('/api/trades/weekly', methods=['GET'])
def get_weekly_trades():
    week_offset = request.args.get('week_offset', default=0, type=int)
    
    today = datetime.now()
    # Assuming Monday is the first day of the week
    start_of_current_week = today - timedelta(days=today.weekday())
    
    # Calculate start and end of the target week
    start_of_week = start_of_current_week - timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    
    # Get trades for the calculated week
    trades = Trade.query.filter(
        Trade.entry_datetime >= start_of_week.replace(hour=0, minute=0, second=0),
        Trade.entry_datetime <= end_of_week.replace(hour=23, minute=59, second=59)
    ).order_by(Trade.entry_datetime).all()
    
    # Group trades by day for the entire week
    trades_by_day = {}
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_str = current_day.strftime('%Y-%m-%d')
        trades_by_day[day_str] = {
            "date": current_day.isoformat(),
            "trades": []
        }
    
    for trade in trades:
        day_str = trade.entry_datetime.strftime('%Y-%m-%d')
        if day_str in trades_by_day:
            trades_by_day[day_str]['trades'].append(trade.to_dict())
            
    return jsonify({
        "week_start": start_of_week.isoformat(),
        "week_end": end_of_week.isoformat(),
        "days": list(trades_by_day.values())
    })

@app.route('/advanced-analysis')
def advanced_analysis():
    return render_template('advanced_analysis.html')

@app.route('/api/advanced-analysis')
def get_advanced_analysis():
    # Get all trades from database
    trades = get_all_trades()
    
    if not trades:
        return jsonify({
            'metrics': {
                'winRate': 0,
                'riskReward': 0,
                'avgWinLoss': 0,
                'profitFactor': 0
            },
            'charts': {
                'equityCurve': {'labels': [], 'data': []},
                'winLossDistribution': {'wins': 0, 'losses': 0},
                'monthlyPerformance': {'labels': [], 'data': []},
                'drawdownAnalysis': {'labels': [], 'data': []}
            }
        })

    # Calculate metrics
    total_trades = len(trades)
    winning_trades = sum(1 for trade in trades if trade['profit'] > 0)
    losing_trades = sum(1 for trade in trades if trade['profit'] < 0)
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_profit = sum(trade['profit'] for trade in trades if trade['profit'] > 0)
    total_loss = abs(sum(trade['profit'] for trade in trades if trade['profit'] < 0))
    
    avg_win = total_profit / winning_trades if winning_trades > 0 else 0
    avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
    
    risk_reward = avg_win / avg_loss if avg_loss != 0 else 0
    profit_factor = total_profit / total_loss if total_loss != 0 else 0

    # Prepare equity curve data
    equity_curve = []
    current_equity = 0
    dates = []
    
    for trade in sorted(trades, key=lambda x: x['date']):
        current_equity += trade['profit']
        equity_curve.append(current_equity)
        dates.append(trade['date'].strftime('%Y-%m-%d'))

    # Calculate drawdown
    drawdown = []
    peak = 0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        drawdown_pct = ((peak - equity) / peak * 100) if peak > 0 else 0
        drawdown.append(drawdown_pct)

    # Calculate monthly performance
    monthly_performance = {}
    for trade in trades:
        month_key = trade['date'].strftime('%Y-%m')
        if month_key not in monthly_performance:
            monthly_performance[month_key] = 0
        monthly_performance[month_key] += trade['profit']

    monthly_labels = sorted(monthly_performance.keys())
    monthly_data = [monthly_performance[month] for month in monthly_labels]

    return jsonify({
        'metrics': {
            'winRate': round(win_rate, 2),
            'riskReward': round(risk_reward, 2),
            'avgWinLoss': round(avg_win / avg_loss if avg_loss != 0 else 0, 2),
            'profitFactor': round(profit_factor, 2)
        },
        'charts': {
            'equityCurve': {
                'labels': dates,
                'data': equity_curve
            },
            'winLossDistribution': {
                'wins': winning_trades,
                'losses': losing_trades
            },
            'monthlyPerformance': {
                'labels': monthly_labels,
                'data': monthly_data
            },
            'drawdownAnalysis': {
                'labels': dates,
                'data': drawdown
            }
        }
    })

def get_all_trades():
    conn = get_db_connection()
    trades = conn.execute('SELECT * FROM trades ORDER BY date').fetchall()
    conn.close()
    return [dict(trade) for trade in trades]

if __name__ == '__main__':
    # The `run_app` function will be the target for our thread
    def run_app():
        app.run(host='127.0.0.1', port=5000)

    # We start the Flask server in a separate thread, so it doesn't block the GUI
    server_thread = threading.Thread(target=run_app)
    server_thread.daemon = True
    server_thread.start()

    # Create and start the pywebview window
    webview.create_window('Trading Journal', 'http://127.0.0.1:5000', width=1280, height=800)
    webview.start()