from models import db
from datetime import datetime

class TradeImage(db.Model):
    __tablename__ = 'trade_images'

    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trades.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    image_type = db.Column(db.String(20), nullable=False)  # ENTRY or EXIT
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'image_path': self.image_path,
            'image_type': self.image_type,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        } 