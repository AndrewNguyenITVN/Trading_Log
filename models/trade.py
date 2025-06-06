from models import db
from datetime import datetime

class Trade(db.Model):
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    entry_datetime = db.Column(db.DateTime, nullable=False)
    exit_datetime = db.Column(db.DateTime, nullable=False)
    instrument = db.Column(db.String(50), nullable=False)
    order_type = db.Column(db.String(10), nullable=False)  # BUY or SELL
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    initial_stop_loss = db.Column(db.Float, nullable=False)
    initial_take_profit = db.Column(db.Float, nullable=False)
    position_size = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # WIN, LOSS, BREAKEVEN
    net_profit = db.Column(db.Float, nullable=False)
    r_value = db.Column(db.Float, nullable=False)
    rationale = db.Column(db.Text)
    review = db.Column(db.Text)
    emotions = db.Column(db.String(100))
    tags = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with TradeImage
    images = db.relationship('TradeImage', backref='trade', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'entry_datetime': self.entry_datetime.isoformat(),
            'exit_datetime': self.exit_datetime.isoformat(),
            'instrument': self.instrument,
            'order_type': self.order_type,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'initial_stop_loss': self.initial_stop_loss,
            'initial_take_profit': self.initial_take_profit,
            'position_size': self.position_size,
            'status': self.status,
            'net_profit': self.net_profit,
            'r_value': self.r_value,
            'rationale': self.rationale,
            'review': self.review,
            'emotions': self.emotions,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'images': [image.to_dict() for image in self.images]
        } 