from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Mechanic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    mon = db.Column(db.Boolean)
    tue = db.Column(db.Boolean)
    wed = db.Column(db.Boolean)
    thu = db.Column(db.Boolean)
    fri = db.Column(db.Boolean)
    sat = db.Column(db.Boolean)
    sun = db.Column(db.Boolean)
