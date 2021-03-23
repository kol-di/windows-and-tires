from flask import Flask, request, jsonify, render_template
import os
import dialogflow
import utility
from db import db, Mechanic


app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule'


db.init_app(app)


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)
        return response.query_result.fulfillment_text


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)

    session_id = data['session'].split('/')[-1]

    if data['queryResult']['action'] == 'add_service':
        service = data['queryResult']['parameters']['service-type']
        reply = {"fulfillmentText": "Вам нужно оказать еще какую-нибудь услугу?",}
        utility.session_info.update_session_info(session_id, 'service_types', service)

        return jsonify(reply)

    if data['queryResult']['action'] == 'choose_mechanic_schedule':
        mechanic = data['queryResult']['parameters']['mechanic']

        utility.session_info.update_session_info(session_id, 'mechanic', mechanic)

        fullfillment_text = \
            'ПН'*(db.session.query().with_entities(Mechanic.mon, Mechanic.name).filter_by(name=mechanic, mon=1).scalar()
                        is not None) + ' ' + \
            'ВТ'*(db.session.query().with_entities(Mechanic.tue, Mechanic.name).filter_by(name=mechanic, tue=1).scalar()
                        is not None) + ' ' + \
            'СР'*(db.session.query().with_entities(Mechanic.wed, Mechanic.name).filter_by(name=mechanic, wed=1).scalar()
                        is not None) + ' ' + \
            'ЧТ'*(db.session.query().with_entities(Mechanic.thu, Mechanic.name).filter_by(name=mechanic, thu=1).scalar()
                        is not None) + ' ' + \
            'ПТ'*(db.session.query().with_entities(Mechanic.fri, Mechanic.name).filter_by(name=mechanic, fri=1).scalar()
                        is not None) + ' ' + \
            'СБ'*(db.session.query().with_entities(Mechanic.sat, Mechanic.name).filter_by(name=mechanic, sat=1).scalar()
                        is not None) + ' ' + \
            'ВС'*(db.session.query().with_entities(Mechanic.sun, Mechanic.name).filter_by(name=mechanic, sun=1).scalar()
                        is not None)

        fullfillment_text = 'Он свободен по следующим дням: ' + ', '.join([x.strip(' ') for x in fullfillment_text.split()]) + \
            '. На какой день вас записать?'
        reply = {"fulfillmentText": fullfillment_text}

        return jsonify(reply)

    if data['queryResult']['action'] == 'choose_schedule':
        utility.session_info.update_session_info(session_id, 'mechanic', 'any')

        fullfillment_text = \
            'ПН' * bool(db.session.query(Mechanic.mon).filter_by(mon=1).count()) + ' ' + \
            'ВТ' * bool(db.session.query(Mechanic.tue).filter_by(tue=1).count()) + ' ' + \
            'СР' * bool(db.session.query(Mechanic.wed).filter_by(wed=1).count()) + ' ' + \
            'ЧТ' * bool(db.session.query(Mechanic.thu).filter_by(thu=1).count()) + ' ' + \
            'ПТ' * bool(db.session.query(Mechanic.fri).filter_by(fri=1).count()) + ' ' + \
            'СБ' * bool(db.session.query(Mechanic.sat).filter_by(sat=1).count()) + ' ' + \
            'ВС' * bool(db.session.query(Mechanic.sun).filter_by(sun=1).count())

        fullfillment_text = 'Можете записаться на следующие дни: ' + ', '.join([x.strip(' ') for x in fullfillment_text.split()]) + \
            '. На какой день вас записать?'
        reply = {"fulfillmentText": fullfillment_text}

        return jsonify(reply)

    if data['queryResult']['action'] == 'choose_day':
        day = data['queryResult']['parameters']['day-of-week']

        mechanic_name = utility.session_info.get_session_info(session_id, 'mechanic', 0)[0]
        if mechanic_name != 'any':
            mechanic = Mechanic.query.filter_by(name=mechanic_name).first()
            if day == 'ПН':
                mechanic.mon = 0
            elif day == 'ВТ':
                mechanic.tue = 0
            elif day == 'СР':
                mechanic.wed = 0
            elif day == 'ЧТ':
                mechanic.thu = 0
            elif day == 'ПТ':
                mechanic.fri = 0
            elif day == 'СБ':
                mechanic.sat = 0
            elif day == 'ВС':
                mechanic.sun = 0
        else:
            if day == 'ПН':
                mechanic = Mechanic.query.filter_by(mon=1).first()
                mechanic.mon = 0
            elif day == 'ВТ':
                mechanic = Mechanic.query.filter_by(tue=1).first()
                mechanic.tue = 0
            elif day == 'СР':
                mechanic = Mechanic.query.filter_by(wed=1).first()
                mechanic.wed = 0
            elif day == 'ЧТ':
                mechanic = Mechanic.query.filter_by(thu=1).first()
                mechanic.thu = 0
            elif day == 'ПТ':
                mechanic = Mechanic.query.filter_by(fri=1).first()
                mechanic.fri = 0
            elif day == 'СБ':
                mechanic = Mechanic.query.filter_by(sat=1).first()
                mechanic.sat = 0
            elif day == 'ВС':
                mechanic = Mechanic.query.filter_by(sun=1).first()
                mechanic.sun = 0

        db.session.commit()

        utility.session_info.update_session_info(session_id, 'day', day)

        if utility.session_info.extract_session_info(session_id, 'mechanic')[0] != 'any':
            fullfillment_text = 'Мы записали вас на ' + utility.session_info.extract_session_info(session_id, 'day')[0] + \
                                ' к механику ' + utility.session_info.extract_session_info(session_id, 'mechanic')[0] + \
                                ' на следующие услуги: ' + ', '.join(utility.session_info.extract_session_info(session_id, 'service_types')) + '.'
        else:
            fullfillment_text = 'Мы записали вас на ' + utility.session_info.extract_session_info(session_id, 'day')[0] + \
                                ' на следующие услуги: ' + ', '.join(utility.session_info.extract_session_info(session_id, 'service_types')) + '.'

        reply = {"fulfillmentText": fullfillment_text}

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
