from flask_sqlalchemy import SQLAlchemy
import datetime


db = SQLAlchemy()


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    start = db.Column(db.DateTime, nullable=False)
    finish = db.Column(db.DateTime, nullable=False)
    employees = db.relationship('Employee', backref="schedule")

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    begin = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    employees = db.relationship('Employee', backref="reservation")


def initalize_timetable(db):
    db.reflect()
    db.drop_all()
    db.create_all()

    employee = 'Дэвид Боуи'
    rec = Employee(name=employee)
    for i in range(1, 30):
        if i % 4 == 1 or i % 4 == 2:
            Schedule(start=datetime.datetime(year=2021, month=5, day=i, hour=9, minute=0),
                            finish=datetime.datetime(year=2021, month=5, day=i, hour=17, minute=0),
                            employees=rec)
    db.session.add(rec)

    employee = 'Эллиот Смит'
    rec = Employee(name=employee)
    for i in range(1, 30):
        if not (i % 7 == 6 or i % 7 == 0):
            Schedule(start=datetime.datetime(year=2021, month=5, day=i, hour=9, minute=0),
                            finish=datetime.datetime(year=2021, month=5, day=i, hour=17, minute=0),
                            employees=rec)
    db.session.add(rec)

    employee = 'Боб Дилан'
    rec = Employee(name=employee)
    for i in range(1, 30):
        if (i % 7 == 1 or i % 7 == 2 or i % 7 == 3):
            Schedule(start=datetime.datetime(year=2021, month=5, day=i, hour=9, minute=0),
                            finish=datetime.datetime(year=2021, month=5, day=i, hour=13, minute=0),
                            employees=rec)
    db.session.add(rec)

    db.session.commit()



