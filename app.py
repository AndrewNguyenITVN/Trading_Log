from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
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
    trades = Trade.query.all()
    return jsonify([trade.to_dict() for trade in trades])

@app.route('/api/trades', methods=['POST'])
def create_trade():
    data = request.json
    trade = Trade(
        entry_datetime=datetime.fromisoformat(data['entry_datetime']),
        exit_datetime=datetime.fromisoformat(data['exit_datetime']),
        instrument=data['instrument'],
        order_type=data['order_type'],
        entry_price=data['entry_price'],
        exit_price=data['exit_price'],
        initial_stop_loss=data['initial_stop_loss'],
        initial_take_profit=data['initial_take_profit'],
        position_size=data['position_size'],
        status=data['status'],
        net_profit=data['net_profit'],
        r_value=data['r_value'],
        rationale=data['rationale'],
        review=data['review'],
        emotions=data['emotions'],
        tags=data['tags']
    )
    db.session.add(trade)
    db.session.commit()
    return jsonify(trade.to_dict()), 201

@app.route('/api/trades/<int:trade_id>', methods=['GET'])
def get_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    return jsonify(trade.to_dict())

@app.route('/api/trades/<int:trade_id>', methods=['PUT'])
def update_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    data = request.json
    for key, value in data.items():
        setattr(trade, key, value)
    db.session.commit()
    return jsonify(trade.to_dict())

@app.route('/api/trades/<int:trade_id>', methods=['DELETE'])
def delete_trade(trade_id):
    try:
        # Get the trade
        trade = Trade.query.get_or_404(trade_id)
        
        # Delete associated images first
        for image in trade.images:
            # Delete image file from uploads directory
            if image.image_path:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
            # Delete image record from database
            db.session.delete(image)
        
        # Delete the trade
        db.session.delete(trade)
        db.session.commit()
        
        return jsonify({'message': 'Trade deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting trade {trade_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    app.run(debug=True) 