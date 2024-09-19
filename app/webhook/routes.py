from flask import Blueprint, json, request, Flask, jsonify,render_template,render_template_string
from datetime import datetime
import pytz
from app import extensions

webhook = Blueprint('Webhook', __name__, url_prefix='/webhook')


def timeconversion(datetime_in):
    def ordinal_suffix(day):
        if 11 <= day <= 13:  # Special case for 11th to 13th
            return f"{day}th"
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        return f"{day}{suffix}"

    # Parse the input string into a datetime object with timezone information
    dt = datetime.fromisoformat(datetime_in)

    # Convert the datetime to UTC
    utc_dt = dt.astimezone(pytz.UTC)

    # Get the day with ordinal suffix
    day_with_suffix = ordinal_suffix(utc_dt.day)

    # Format the datetime into the desired output format
    formatted_date = utc_dt.strftime(f"{day_with_suffix} %B %Y - %I:%M %p UTC")

    return formatted_date


@webhook.route('/receiver', methods=["POST"])
def receiver():
    payload=request.json
    event_type = request.headers.get('X-GitHub-Event')
    if event_type=="push" and not len(payload.get('commits'))>1 : 
        timestamp=timeconversion(payload['commits'][0]['timestamp'])
        mongo_data={
            "RequestId": payload['after'],
            "Author": payload['commits'][0]['author']['name'],
            "Action": "push",
            "From_Branch": "",
            "To_Branch":str(payload['ref']).split('/')[-1],
            "TimeStamp":timestamp
        }
        print(f"{payload['commits'][0]['author']['name']} pushed to {str(payload['ref']).split('/')[-1]} on {timestamp}")
        mongo=extensions.connect() 
        mongo.db.events.insert_one(mongo_data)

    elif event_type=="pull_request" and payload['action']=="opened":
        timestamp=timeconversion(payload['pull_request']['base']['repo']['created_at']) 
        mongo_data={
            "RequestId":payload['pull_request']['base']['sha'],
            "Author": payload['pull_request']['base']['user']['login'],
            "Action": "pull_request",
            "From_Branch":payload['pull_request']['base']['ref'],
            "To_Branch":payload['pull_request']['head']['ref'],
            "TimeStamp":timestamp
        } 
        print(f"{payload['pull_request']['base']['user']['login']} submitted a pull request from {payload['pull_request']['head']['ref']}  to {payload['pull_request']['base']['ref']} on {timestamp}")
        mongo=extensions.connect() 
        mongo.db.events.insert_one(mongo_data)


    elif event_type=="pull_request" and payload['action']=="closed":
        timestamp=timeconversion(payload['pull_request']['base']['repo']['created_at'])
        mongo_data={
            "RequestId":payload['pull_request']['base']['sha'],
            "Author": payload['pull_request']['base']['user']['login'],
            "Action": "merge",
            "From_Branch":payload['pull_request']['base']['ref'],
            "To_Branch":payload['pull_request']['head']['ref'],
            "TimeStamp":timestamp
        }
        print(f"{payload['pull_request']['base']['user']['login']} merged branch  {payload['pull_request']['head']['ref']}  to {payload['pull_request']['base']['ref']} on {timestamp}")
        mongo=extensions.connect() 
        mongo.db.events.insert_one(mongo_data)

    # print(event_type,payload)
    return "Webhook received!", 200


@webhook.route('/events/latest', methods=['GET'])
def get_latest_events():
    mongo=extensions.connect()
    # # Fetch the latest 10 events
    result = []
    for event in ["push","merge","pull_request"]:
        events1 = mongo.db.events.find({"Action": event}).sort("TimeStamp", -1).limit(10)
        if event=="push":
            for ev1 in list(events1):
                result.append({"push":f'{ev1["Author"]} pushed to {ev1["To_Branch"]} on {ev1["TimeStamp"]}'})   
        elif event=="pull_request":
            for ev2 in list(events1):
                result.append({"pull_request":f'{ev2["Author"]} submitted a pull request from {ev2["From_Branch"]} to {ev2["To_Branch"]} on {ev2["TimeStamp"]}'})
        elif event=="merge":
            for ev3 in list(events1):
                result.append({"merge":f'{ev3["Author"]} merged branch from {ev3["From_Branch"]} to {ev3["To_Branch"]} on {ev3["TimeStamp"]}'})
    
    return render_template('index.html', events=result, refresh_interval=15)