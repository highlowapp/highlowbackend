from flask import Flask, request
from EventLogger import EventLogger
import json
import Helpers

#Create a Flask app instance
app = Flask(__name__)

#MySQL configuration
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")


#Create an event logger instance
event_logger = EventLogger(mysql_config["host"], mysql_config["username"], mysql_config["password"], mysql_config["database"])

#Create the `log_event` route
@app.route("/log_event", methods=["POST"])
def log_event():
    return event_logger.log_event( request.form["event_type"], request.form["data"], request.form["admin_password"] )


#Create the get event
@app.route("/query", methods=["GET"])
def query():
    _type = request.args.get("type")
    min_time = request.args.get("min_time")
    max_time = request.args.get("max_time")
    conditions = json.loads( request.args.get("conditions") )

    return event_logger.query( _type=_type, min_time=min_time, max_time=max_time, conditions=conditions, admin_password=request.args["admin_password"] )
