from flask import Flask, request, jsonify, render_template
from sqlalchemy import and_, or_, not_, extract
from datetime import timedelta, datetime
import os
import dialogflow
import arrow
import uuid
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
    user_id = uuid.uuid4()
    return render_template('index.html', user_id=user_id)


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
        date_time = arrow.get(date_time['date_time']).datetime

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

        def day_off(emp_id):
            return not db.session.query(Schedule).filter(and_(or_(Schedule.emp_id == emp_id, emp_id == 0),
                    extract('day', Schedule.start) == date_time.day)).all()

        if day_off(emp_id):
            fulfillment_text = "Извините, он не работает в этот день. Скажите другую дату, которая будет вам удобна"
            if emp_id == 0: fulfillment_text = \
                "Извините, в этот день никто не работает. Скажите другую дату, котрая будет вам удобна"

            reply = {"fulfillmentText": fulfillment_text}
            return jsonify(reply)

        def too_early(emp_id):
            return not db.session.query(Schedule).filter(and_(or_(Schedule.emp_id == emp_id, emp_id == 0),
                or_(extract('hour', Schedule.start) < date_time.hour,
                and_(extract('hour', Schedule.start) == date_time.hour,
                extract('minute', Schedule.start) <= date_time.minute)))).all()

        if too_early(emp_id):
            fulfillment_text = "Извините, слишком рано. Выберите, пожалуйста, время попозже"
            reply = {"fulfillmentText": fulfillment_text}
            return jsonify(reply)

        def too_late(emp_id):
            return not db.session.query(Schedule).filter(and_(or_(Schedule.emp_id == emp_id, emp_id == 0),
                or_(extract('hour', Schedule.finish) > (date_time + timedelta(minutes=duration)).hour,
                and_(extract('hour', Schedule.finish) == (date_time + timedelta(minutes=duration)).hour,
                extract('minute', Schedule.finish) >= (date_time + timedelta(minutes=duration)).minute)))).all()

        if too_late(emp_id):
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

        def reservation_info_text(session_id):
            return "Мы вас записали! Ваш мастер " + utility.session_info.extract_session_info(session_id, 'mechanic')[0] +\
            ". Выбранные услуги " + " ".join(utility.session_info.extract_session_info(session_id, 'service_types'))

        if emp_id:
            if assignmnet_booked(emp_id, date_time, duration):
                fulfillment_text = "Извините, это время уже зарезервировано. Выберите, пожалуйста, другое время"
            else:
                note = Reservation(begin=date_time, end=date_time+timedelta(minutes=duration), emp_id=emp_id)
                db.session.add(note)
                db.session.commit()
                fulfillment_text = reservation_info_text(session_id)

        else:
            fulfillment_text = "Извините, на это время нет записей. Пожалуйста, выберите другое"
            for id_unf in db.session.query(Employee.id):
                id = int(id_unf[0])
                if assignmnet_booked(id, date_time, duration) or too_late(id) or too_early(id) or day_off(id):
                    continue
                else:
                    note = Reservation(begin=date_time, end=date_time+timedelta(minutes=duration), emp_id=id)
                    db.session.add(note)
                    db.session.commit()
                    utility.session_info.change_session_info(session_id, 'mechanic', Employee.query.filter_by(id=id).first().name)
                    fulfillment_text = reservation_info_text(session_id)
                    break

        reply = {"fulfillmentText": fulfillment_text}
        return jsonify(reply)


@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    user_id = request.form['uuid']
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    fulfillment_text = detect_intent_texts(project_id, user_id, message, 'ru')
    response_text = {"message":  fulfillment_text}
    return jsonify(response_text)


# run Flask app
if __name__ == "__main__":
    #app.run()
    #app.run(host="192.168.0.88", port=5000, debug=True, threaded=False)
    app.run(host="0.0.0.0", port=5000, debug=False)
