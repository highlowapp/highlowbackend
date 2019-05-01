from flask import Flask, request
import Helpers
import requests
import json
from services.Auth import Auth
from services.HLEmail import HLEmail
from services.User import User
from services.HighLow import HighLow, HighLowList
from services.EventLogger import EventLogger
from services.Notifications import Notifications


#MySQL server configuration
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")

host = mysql_config["host"]
username = mysql_config["username"]
password = mysql_config["password"]
database = mysql_config["database"]

#Auth service
auth_service = Helpers.service("auth")

#Create an Auth instance
auth = Auth(auth_service, host, username, password, database)

#Instantiate HLEmail
email_config = Helpers.read_json_from_file("config/email_config.json")
hlemail = HLEmail(email_config["email"])

#Create an event logger instance
event_logger = EventLogger(host, username, password, database)

#Create a Notifications instance
notifs = Notifications(host, username, password, database)



#Placeholders for HTML
sign_up_html = ""
sign_in_html = ""
reset_password_html = ""

#Get the HTML for the sign up page
with open("signUp.html", 'r') as file:
    sign_up_html = file.read()

#Get the HTML for the sign in page
with open("signIn.html", 'r') as file:
    sign_in_html = file.read()

#Get the HTML for the reset password page
with open("resetPassword.html", 'r') as file:
    reset_password_html = file.read()


#Create flask app
app = Flask(__name__)



#Define app routes

#######################
# Authentication      #
#######################

#Sign_up
@app.route("/auth/sign_up", methods=["GET", "POST"])
def sign_up():

    if request.method == "POST":

        return auth.sign_up( request.form["firstname"], request.form["lastname"], request.form["email"], request.form["password"], request.form["confirmpassword"] )
    
    return sign_up_html

#Sign_in
@app.route("/auth/sign_in", methods=["GET", "POST"])
def sign_in():

    if request.method == "POST":

        return auth.sign_in( request.form["email"], request.form["password"] )

    return sign_in_html

#Reset password
@app.route("/auth/password_reset/<string:reset_id>", methods=["GET", "POST"])
def password_reset(reset_id):
    
    if request.method == "POST":
        
        return auth.reset_password( reset_id, request.form["password"], request.form["confirmpassword"] )

    return reset_password_html

#Send password reset email
@app.route("/auth/forgot_password", methods=["POST"])
def forgot_password():
    
    return auth.send_password_reset_email( request.form["email"] )

#Verify token
@app.route("/auth/verify_token", methods=["GET", "POST"])
def verify_token():
    #Retrieve the token
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Attempt to validate the token
    result = auth.validate_token(token)

    #If token is invalid...
    if result == "ERROR-INVALID-TOKEN":
        #Return an error
        return '{ "error": "' + result + '" }'

    #Otherwise, return the UID
    return '{ "uid": "' + result + '" }'

#Blacklist token
@app.route("/auth/blacklist/<string:token>", methods=["GET", "POST"])
def blacklist_token(token):
    auth.blacklist_token(token)
    return '{"status":"success"}'










#######################
# Email               #
#######################

@app.route("/email/send_html_email", methods=["POST"])
def send_html_email():
	hlemail.send_html_email( request.form["email"], request.form["message"], request.form["password"] )

@app.route("/email/send_email", methods=["POST"])
def send_email():
	hlemail.send_email( request.form["email"], request.form["message"], request.form["password"] )











#######################
# User                #
#######################

@app.route("/user/get/<string:property>", methods=["POST"])
def get(property):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Create the headers
    headers = { 'Authorization': "Bearer " + token }

    #Make a request to the Auth service
    token_verification_request = requests.post("http://{}/verify_token".format(auth_service), headers=headers)

    #Obtain the result as JSON
    result = token_verification_request.json()

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    #Otherwise, get the user
    user = User(result["uid"], host, username, password, database)

    #Get the specified property
    prprty = getattr(user, property)

    return '{ "' + property + '": "' + prprty + '"}'


@app.route("/user/set/<string:property>", methods=["POST"])
def set(property):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Create the headers
    headers = { 'Authorization': "Bearer " + token }

    #Make a request to the Auth service
    token_verification_request = requests.post("https://{}/verify_token".format(auth_service), headers=headers)

    #Obtain the result as JSON
    result = token_verification_request.json()

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'


    #Otherwise, get the user
    user = User(result["uid"], host, username, password, database)

    #Set the specified property
    user.set_column(property, request.form["value"])

    return '{ "status": "success" }'







#######################
# HighLow             #
#######################
@app.route("/highlow/set/<string:highlowid>", methods=["POST"])
def setproperty(highlowid):
	#Verify auth token
	token = request.headers["Authentication"].replace("Bearer ", "")

	verification = Helpers.verify_token(token)

	if 'error' in verification:
		return verification

	else:
		uid = verification["uid"]

		high = request.form.get("high") or ""
		low = request.form.get("low") or ""

		highlow = None

		if "highlowid" in request.form:
			highlow = HighLow(host, username, password, database, request.form["highlowid"])
			highlow.update(high, low)

		else:
			highlow = HighLow(host, username, password, database)
			highlow.create(uid, high, low)


@app.route("/highlow/like/<string:highlowid>", methods=["POST"])
def like(highlowid):
    #Verify auth token
	token = request.headers["Authentication"].replace("Bearer ", "")

	verification = Helpers.verify_token(token)

	if 'error' in verification:
		return verification

	else:
		uid = verification["uid"]

		if 'highlowid' in request.form:
			highlow = HighLow(host, username, password, database, request.form["highlowid"])
			highlow.like(uid)

		else:
			return json.dumps({'error':'Must provide HighLow ID'})


@app.route("/highlow/comment/<string:highlowid>", methods=["POST"])
def comment(highlowid):
    #Verify auth token
	token = request.headers["Authentication"].replace("Bearer ", "")

	verification = Helpers.verify_token(token)

	if 'error' in verification:
		return verification

	else:
		uid = verification["uid"]
		message = request.form.get("message") or ""

		if 'highlowid' in request.form:
			highlow = HighLow(host, username, password, database, request.form["highlowid"])
			highlow.comment(uid, message)

		else:
			return json.dumps({'error':'Must provide HighLow ID'})


#TODO: Add endpoints for getting specific highlows, getting all highlows for user and sorting, etc.
#Those endpoints will make use of the "HighLowList" class
@app.route("/highlow/get/today", methods=["GET"])
def get_today():
	#Verify auth token
	token = request.headers["Authentication"].replace("Bearer ", "")

	verification = Helpers.verify_token(token)

	if 'error' in verification:
		return verification

	else:
		uid = verification["uid"]
		
		#Now, we use `HighLowList` to get today's highlow
		highlowlist = HighLowList(host, username, password, database)

		today_highlow = highlowlist.get_today_for_user(uid)

		return json.dumps(today_highlow)


@app.route("/highlow/get/user", methods=["GET"])
def get_user():
	#Verify auth token
	token = request.headers["Authentication"].replace("Bearer ", "")

	verification = Helpers.verify_token(token)

	if 'error' in verification:
		return verification

	else:
		#Defaults to the current user
		uid = request.args.get("uid") or verification["uid"]

		highlowlist = HighLowList(host, username, password, database)

		highlows = highlowlist.get_highlows_for_user(uid, sortby=request.args.get("sortby"), limit=request.args.get("limit"))

		return json.dumps(highlows)









#######################
# EventLogger         #
#######################

#Create the `log_event` route
@app.route("/eventlogger/log_event", methods=["POST"])
def log_event():
    return event_logger.log_event( request.form["event_type"], request.form["data"], request.form["admin_password"] )


@app.route("/eventlogger/query", methods=["GET"])
def query():
    _type = request.args.get("type")
    min_time = request.args.get("min_time")
    max_time = request.args.get("max_time")
    conditions = json.loads( request.args.get("conditions") )

    return event_logger.query( _type=_type, min_time=min_time, max_time=max_time, conditions=conditions, admin_password=request.args["admin_password"] )








#######################
# Notifications       #
#######################

@app.route("/notifications/register", methods=["POST"])
def register():

    #Retrieve the token
    token = request.headers["Authorization"].replace("Bearer ", "")

    token_verification = Helpers.verify_token(token)

    if 'error' in token_verification:
        return token_verification

    uid = token_verification["uid"]
    
    return notifs.register_device( request.form["platform"], request.form["device_id"], uid )




@app.route("/notifications/send", methods=["POST"])
def send():

    device_filter = request.form.get("device_filter") or "."
    platform = request.form.get("platform") or 0
    random_drop = request.form.get("random_drop") or 0

    notifs.send_notification( request.form["title"], request.form["message"], device_filter=device_filter, platform=platform, random_drop=random_drop, admin_password=request.form["admin_password"] )

    return "request pending"



#TODO: Add File Storage Service



if __name__ == '__main__':
	app.run(host='0.0.0.0')

    #Run tests
    auth.run_tests()
