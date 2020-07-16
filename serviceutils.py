from services.Auth import Auth
from services.HLEmail import HLEmail
from services.EventLogger import EventLogger
from services.User import User
import json
import Helpers


#MySQL config
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")

host = mysql_config["host"]
username = mysql_config["username"]
password = mysql_config["password"]
database = mysql_config["database"]


#Auth service
auth_service = Helpers.service("auth")
auth = Auth(auth_service, host, username, password, database)

#Email Config
email_config = Helpers.read_json_from_file("config/email_config.json")

#Email service
email_service = Helpers.service("email")

hlemail = HLEmail(email_config["email"])


#Event logger
event_logger_config = Helpers.read_json_from_file("config/eventlogger_config.json")
event_logger = EventLogger(host, username, password, database)


def verify_token(token):
    result = auth.validate_token(token)

    #If token is invalid...
    if result == "ERROR-INVALID-TOKEN":
        #Return an error
        return json.loads('{ "error": "' + result + '" }')

    #Otherwise, return the UID
    return json.loads('{ "uid": "' + result + '" }')

def get_current_user(request):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")
    verification = verify_token(token)
    if 'error' in verification:
        return None, '{ "error": "' + verification['error'] + '" }'
    return verification.get('uid'), None

def verify_admin_token(token):
    result = auth.validate_admin_token(token)

    #If token is invalid...
    if result == "ERROR-INVALID-TOKEN":
        #Return an error
        return json.loads('{ "error": "' + result + '" }')

    #Otherwise, return the UID
    return json.loads('{ "user": "' + result + '" }')

### DON'T USE UNLESS ABSOLUTELY SURE. USE `verify_token` INSTEAD ###
def verify_token_accept_old(token):
    result = auth.validate_token(token, accepts_old=True)

    if result == "ERROR-INVALID-TOKEN":
        return {
            "error": result
        }
    
    return {
        "uid": result
    }

def send_email(recipient, subject, message):
    hlemail.send_email(recipient, subject, message, email_config["password"])

def log_event(type, data):
    event_logger.log_event(type, data, event_logger_config["admin_password"])


def upload_default_profile_picture(uid):
	#Copy the default profile image
	user = User(uid, host, username, password, database)

	user.set_default_profile_image()

