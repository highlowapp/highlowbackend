from services.Auth import Auth
from services.HLEmail import HLEmail
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


def verify_token(token):
    result = auth.validate_token(token)

    #If token is invalid...
    if result == "ERROR-INVALID-TOKEN":
        #Return an error
        return '{ "error": "' + result + '" }'

    #Otherwise, return the UID
    return '{ "uid": "' + result + '" }'

def send_email(recipient, message):
    hlemail.send_html_email(recipient, message, email_config["password"])
