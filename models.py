from database import db
from flask_login import UserMixin
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from datetime import datetime

_ph = PasswordHasher()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='company') # 'admin' or 'company'
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = _ph.hash(password)

    def check_password(self, password):
        try:
            return _ph.verify(self.password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    fantasy_name = db.Column(db.String(150), nullable=True) # Nome Fantasia
    contact_email = db.Column(db.String(150), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref='company', uselist=False, cascade="all, delete-orphan")
    # Relationship to items (folders/links)
    items = db.relationship('Item', backref='company', cascade="all, delete-orphan", lazy=True)
    # Relationship to bug reports
    bug_reports = db.relationship('BugReport', backref='company', cascade="all, delete-orphan", lazy=True)

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(10), nullable=False) # 'folder' or 'link'
    url = db.Column(db.String(500), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True) # Data de validade do link
    link_password = db.Column(db.String(100), nullable=True) # Senha opcional para o link
    parent_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    refresh_requested_at = db.Column(db.DateTime, nullable=True)
    
    # Recursive relationship for folders
    children = db.relationship('Item', backref=db.backref('parent', remote_side=[id]), cascade="all, delete-orphan")

class BugReport(db.Model):
    __tablename__ = 'bug_reports'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending') # 'pending', 'resolved'
    report_type = db.Column(db.String(20), default='manual') # 'manual' or 'expiration'
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    related_item = db.relationship('Item', backref='refresh_reports', foreign_keys=[item_id])
    user_reporter = db.relationship('User', backref='bug_reports')
