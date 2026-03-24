from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class AreaCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    area_name = db.Column(db.String(100), nullable=False)
    
    residents = db.relationship('User', backref='area', lazy=True)

    def __repr__(self):
        return f'<AreaCode {self.code} - {self.area_name}>'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='resident')
    
    specialization = db.Column(db.String(50), nullable=True) 
   
    availability = db.Column(db.String(20), nullable=False, default='Off Duty')
   
    profile_image = db.Column(db.String(255), nullable=True) 
    
    is_active = db.Column(db.Boolean, default=True)
    
    area_code_id = db.Column(db.Integer, db.ForeignKey('area_code.id'), nullable=False)
    
    incidents = db.relationship('Incident', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f'<User {self.first_name} {self.last_name} - Role: {self.role}>'

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_type = db.Column(db.String(100), nullable=False) 
    severity = db.Column(db.String(20), nullable=False) 
    
    location = db.Column(db.String(200), nullable=False)
    
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    description = db.Column(db.Text, nullable=False)
    media_path = db.Column(db.String(255), nullable=True) 
    status = db.Column(db.String(50), nullable=False, default='Pending')
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    is_anonymous = db.Column(db.Boolean, default=False)
    internal_notes = db.Column(db.Text, nullable=True)
    eta = db.Column(db.String(50), nullable=True)
    resident_feedback = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Incident {self.id} - {self.incident_type}>'