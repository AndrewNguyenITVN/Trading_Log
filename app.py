from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import json
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///D:/myproject/Trading/data/trading_journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'data/images'
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
            net_profit=float(data['net_profit']),
            r_value=float(data['r_value']),
            rationale=data['rationale'],
            review=data['review'],
            emotions=data['emotions'],
            tags=data['tags']
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/trades/<int:trade_id>', methods=['GET'])
def get_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    return jsonify(trade.to_dict())

@app.route('/api/trades/<int:trade_id>', methods=['PUT'])
def update_trade(trade_id):
    try:
        trade = Trade.query.get_or_404(trade_id)
        data = request.form.to_dict()
        
        # Update trade fields
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

        # Handle image uploads for update
        if 'entry_image' in request.files and request.files['entry_image'].filename != '':
            upload_image_for_trade(request.files['entry_image'], trade.id, 'ENTRY', data.get('entry_image_description'))
        
        if 'exit_image' in request.files and request.files['exit_image'].filename != '':
            upload_image_for_trade(request.files['exit_image'], trade.id, 'EXIT', data.get('exit_image_description'))
        
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

def upload_image_for_trade(file, trade_id, image_type, description):
    if file and allowed_file(file.filename):
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
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Save file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Create database record
        image = TradeImage(
            trade_id=trade_id,
            image_path=unique_filename,
            image_type=request.form.get('image_type', 'ENTRY'),
            description=request.form.get('description', '')
        )
        db.session.add(image)
        db.session.commit()
        
        return jsonify(image.to_dict()), 201
    
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
    # Calculate statistics using pandas
    # This is a placeholder - implement actual statistics calculation
    return jsonify({
        'total_trades': len(trades),
        'win_rate': 0,
        'profit_factor': 0,
        'expectancy': 0
    })

@app.route('/api/trades/weekly', methods=['GET'])
def get_weekly_trades():
    week_offset = request.args.get('week_offset', default=0, type=int)
    
    # Calculate the start and end of the week
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday() + (week_offset * 7))
    end_of_week = start_of_week + timedelta(days=6)
    
    # Get trades for the week
    trades = Trade.query.filter(
        Trade.entry_datetime >= start_of_week,
        Trade.entry_datetime <= end_of_week
    ).order_by(Trade.entry_datetime).all()
    
    # Group trades by day
    trades_by_day = {}
    for trade in trades:
        day = trade.entry_datetime.strftime('%Y-%m-%d')
        if day not in trades_by_day:
            trades_by_day[day] = []
        trades_by_day[day].append(trade.to_dict())
    
    # Create a list of all days in the week
    week_days = []
    current_day = start_of_week
    while current_day <= end_of_week:
        day_str = current_day.strftime('%Y-%m-%d')
        week_days.append({
            'date': day_str,
            'trades': trades_by_day.get(day_str, [])
        })
        current_day += timedelta(days=1)
    
    return jsonify({
        'week_start': start_of_week.strftime('%Y-%m-%d'),
        'week_end': end_of_week.strftime('%Y-%m-%d'),
        'days': week_days
    })

if __name__ == '__main__':
    app.run(debug=True) 