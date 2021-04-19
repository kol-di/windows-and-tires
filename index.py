from flask import Flask, request, jsonify, render_template
from sqlalchemy import and_, or_, not_, extract
from datetime import timedelta, datetime
import os
import dialogflow
import arrow
import utility
from db import db, Employee, Schedule, Reservation, initalize_timetable


app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule'


db.init_app(app)


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        text_input = dialogflow.types.TextInput(text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        response = session_client.detect_intent(session=session, query_input=query_input)
        return response.query_result.fulfillment_text


@app.route('/')
def index():
    ## uncomment and run to set contents of all tables to the test dataset
    # initalize_timetable(db)
    return render_template('index.html')


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)

    session_id = data['session'].split('/')[-1]

    if data['queryResult']['action'] == 'add_service':
        service = data['queryResult']['parameters']['service-type']
        reply = {"fulfillmentText": "Вам нужно оказать еще какую-нибудь услугу?"}
        utility.session_info.update_session_info(session_id, 'service_types', service)

        return jsonify(reply)

    if data['queryResult']['action'] == 'choose_mechanic_schedule':
        mechanic = data['queryResult']['parameters']['mechanic']

        utility.session_info.update_session_info(session_id, 'mechanic', mechanic)

        emp_id = Employee.query.filter_by(name=mechanic).first().id
        print('emp_id в choose_mechanic_schedule', emp_id)
        fulfillment_text = "Ближайшие дни он работает: "
        date_schedule = db.session.query(Schedule).filter(Schedule.emp_id == emp_id).all()[0:7]

        for hours in date_schedule:
            fulfillment_text += "\n" + str(hours.start.day) + " с " + str(hours.start.hour) + \
                                " до " + str(hours.finish.hour) + ", "

        fulfillment_text += ". Когда вам будет удобно?"
        reply = {"fulfillmentText": fulfillment_text}

        return jsonify(reply)

    if data['queryResult']['action'] == 'choose_schedule':
        utility.session_info.update_session_info(session_id, 'mechanic', 'any')
        fulfillment_text = 'На какую дату вас записать?'
        reply = {"fulfillmentText": fulfillment_text}

        return jsonify(reply)

    if data['queryResult']['action'] == 'choose_date_time':
        date_time = data['queryResult']['parameters']['date-time']
        print(date_time)
        date_time = arrow.get(date_time['date_time']).datetime
        print(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute)

        services = utility.session_info.extract_session_info(session_id, 'service_types')
        duration = 0
        if 'мойка' in services: duration += 30
        if 'шиномонтаж' in services: duration += 60
        if 'замена стекла' in services: duration += 90

        mechanic = utility.session_info.extract_session_info(session_id, 'mechanic')[0]
        if mechanic == 'any':
            emp_id = 0
        else:
            emp_id = Employee.query.filter_by(name=mechanic).first().id
        print(emp_id)

        if not db.session.query(Schedule).filter(and_(or_(Schedule.emp_id == emp_id, emp_id == 0),
                extract('day', Schedule.start) == date_time.day)).all():
            fulfillment_text = "Извините, он не работает в этот день. Скажите другую дату, которая будет вам удобна"
            if emp_id == 0: fulfillment_text = \
                "Извините, в этот день никто не работает. Скажите другую дату, котрая будет вам удобна"

            reply = {"fulfillmentText": fulfillment_text}
            return jsonify(reply)

        if not db.session.query(Schedule).filter(and_(or_(Schedule.emp_id == emp_id, emp_id == 0),
                or_(extract('hour', Schedule.start) < date_time.hour,
                and_(extract('hour', Schedule.start) == date_time.hour,
                extract('minute', Schedule.start) <= date_time.minute)))).all():
            fulfillment_text = "Извините, слишком рано. Выберите, пожалуйста, время попозже"

            reply = {"fulfillmentText": fulfillment_text}
            return jsonify(reply)

        if not db.session.query(Schedule).filter(and_(or_(Schedule.emp_id == emp_id, emp_id == 0),
                or_(extract('hour', Schedule.finish) > (date_time + timedelta(minutes=duration)).hour,
                and_(extract('hour', Schedule.finish) == (date_time + timedelta(minutes=duration)).hour,
                extract('minute', Schedule.finish) > (date_time + timedelta(minutes=duration)).minute)))).all():
            fulfillment_text = "Извините, слишком поздно закончим. Выберите, пожалуйста, время пораньше"

            reply = {"fulfillmentText": fulfillment_text}
            return jsonify(reply)

        def assignmnet_booked(emp_id, date_time, duration):
            return db.session.query(Reservation).filter(and_(and_(extract('day', Reservation.begin) == date_time.day,
                                                            Reservation.emp_id == emp_id),
            not_(or_(or_(extract('hour', Reservation.begin) > (date_time + timedelta(minutes=duration)).hour,
            and_(extract('hour', Reservation.begin) == (date_time + timedelta(minutes=duration)).hour,
            extract('minute', Reservation.begin) >= (date_time + timedelta(minutes=duration)).minute)),
            or_(extract('hour', Reservation.end) < date_time.hour,
            and_(extract('hour', Reservation.end) == date_time.hour,
            extract('minute', Reservation.end) <= date_time.minute)))))).all()

        if emp_id:
            if assignmnet_booked(emp_id, date_time, duration):
                print(assignmnet_booked(emp_id, date_time, duration))
                fulfillment_text = "Извините, это время уже зарезервировано. Выберите, пожалуйста, другое время"
            else:
                note = Reservation(begin=date_time, end=date_time+timedelta(minutes=duration), emp_id=emp_id)
                db.session.add(note)
                db.session.commit()
                fulfillment_text = "Мы вас записали!"

        else:
            fulfillment_text = "Извините, это время уже зарезервировано. Выберите, пожалуйста, другое время"
            for id in db.session.query(Employee.id).all()[0]:
                print('emp_id в choose_date_time (механик указан)', id)
                if assignmnet_booked(id, date_time, duration):
                    print(assignmnet_booked(id, date_time, duration))
                    pass
                else:
                    note = Reservation(begin=date_time, end=date_time+timedelta(minutes=duration), emp_id=id)
                    db.session.add(note)
                    db.session.commit()
                    fulfillment_text = "Мы вас записали!"

        reply = {"fulfillmentText": fulfillment_text}
        return jsonify(reply)


@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    fulfillment_text = detect_intent_texts(project_id, "unique", message, 'ru')
    response_text = {"message":  fulfillment_text}
    return jsonify(response_text)


# run Flask app
if __name__ == "__main__":
    app.run()
