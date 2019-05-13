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
import serviceutils
from urllib.parse import unquote


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
        result =  auth.sign_up( request.form["firstname"], request.form["lastname"], request.form["email"], request.form["password"], request.form["confirmpassword"] )
        
        if "error" in result:
            result =  auth.sign_up( request.form["firstname"], request.form["lastname"], request.form["email"], request.form["password"], request.form["confirmpassword"] )

            serviceutils.log_event("sign_up_error", {
                        "uid": result["uid"],
                        "error": result["error"]
                        })
        else:
            serviceutils.log_event("user_signed_up", {
                        "uid": result["uid"]   
                        })
    
        return result

    return sign_up_html
        
        
    

#Sign_in
@app.route("/auth/sign_in", methods=["GET", "POST"])
def sign_in():

    

    if request.method == "POST":

        result = auth.sign_in( request.form["email"], request.form["password"] )

        if "error" in result:

            serviceutils.log_event("sign_in_error", {
                        "uid": result["uid"],
                        "error": result["error"]
                        })

        else:
            serviceutils.log_event("user_signed_in", {
                        "uid": result["uid"]   
                        })
 
        return result

    return sign_in_html


#Reset password
@app.route("/auth/password_reset/<string:reset_id>", methods=["GET", "POST"])
def password_reset(reset_id):
    

    if request.method == "POST":
        result = auth.reset_password( reset_id, request.form["password"], request.form["confirmpassword"] )
        
        if result == "success":

            serviceutils.log_event("user_reset_password", {
                        "uid": result["uid"],
                        })

        else:
            serviceutils.log_event("error_in_reseting_password", {
                        "uid": result["uid"],
                        "error": result
                        })

        return result

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

        serviceutils.log_event("invalid_token", {
                    "error": result,
                    "false_token": token
                    #Add IP address of the computer here 
                    })

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

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

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

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request.json()

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'


    #Otherwise, get the user
    user = User(result["uid"], host, username, password, database)

    if property != "profileimage":
        #Set the specified property
        user.set_column(property, request.form["value"])
    else:
        image = request.files.get("file")

        if not image:
            return '{"error":"no-file-uploaded"}'
        
        user.set_profileimage(image, result["uid"])

    return '{ "status": "success" }'


@app.route("/user/flag/<string:user>", methods=["POST"])
def flag(user):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request.json()

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    try:
        user = User(user, host, username, password, database)
    except:
        return '{ "error": "user-no-exist" }'

    return user.flag(flagger)

@app.route("/user/unflag/<string:user>", methods=["POST"])
def unflag(user):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request.json()

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    try:
        user = User(user, host, username, password, database)
    except:
        return '{ "error": "user-no-exist" }'

    return user.unflag(flagger)










#######################
# HighLow             #
#######################
@app.route("/highlow/set/high", methods=["POST"])
def sethigh():
    #Verify auth token
    token = request.headers["Authentication"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return verification

    uid = verification["uid"]

    high = request.form.get("high")
    high_image = request.files.get("file")

    highlow = None

    if "highlowid" in request.form:
        highlow = HighLow(host, username, password, database, high_low_id=request.form["highlowid"])
        highlow.update_high(text=high, image=high_image)

    else:
        highlow = HighLow(host, username, password, database)
        highlow.create(uid, high=high, low=None, high_image=high_image, low_image=None)


@app.route("/highlow/set/low", methods=["POST"])
def setlow():
    #Verify auth token
    token = request.headers["Authentication"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return verification

    uid = verification["uid"]

    low = request.form.get("low")
    low_image = request.files.get("file")

    highlow = None

    if "highlowid" in request.form:
        highlow = HighLow(host, username, password, database, high_low_id=request.form["highlowid"])
        highlow.update_low(text=low, image=low_image)

    else:
        highlow = HighLow(host, username, password, database)
        highlow.create(uid, high=None, low=low, high_image=None, low_image=low_image)


@app.route("/highlow/like/<string:highlowid>", methods=["POST"])
def like(highlowid):
    #Verify auth token
	token = request.headers["Authentication"].replace("Bearer ", "")

	verification = serviceutils.verify_token(token)

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

	verification = serviceutils.verify_token(token)

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

	verification = serviceutils.verify_token(token)

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

	verification = serviceutils.verify_token(token)

	if 'error' in verification:
		return verification

	else:
		#Defaults to the current user
		uid = request.args.get("uid") or verification["uid"]

		highlowlist = HighLowList(host, username, password, database)

		highlows = highlowlist.get_highlows_for_user(uid, sortby=request.args.get("sortby"), limit=request.args.get("limit"))

		return json.dumps(highlows)








@app.route("/highlow/flag/<string:highlowid>", methods=["POST"])
def flaghighlow(highlowid):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request.json()

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    try:
        highlow = HighLow(host, username, password, database, high_low_id=highlowid)
    except:
        return '{ "error": "highlow-no-exist" }'

    return highlow.flag(flagger)


@app.route("/highlow/unflag/<string:highlowid>", methods=["POST"])
def unflaghighlow(highlowid):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request.json()

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    try:
        highlow = HighLow(host, username, password, database, high_low_id=highlowid)
    except:
        return '{ "error": "highlow-no-exist" }'

    return highlow.unflag(flagger)













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

    conditions_raw = request.args.get("conditions")
    conditions = None
    if conditions_raw:
        conditions_json_str = unquote(conditions_raw)

        print(conditions_json_str)

        conditions = json.loads( conditions_json_str )

    return event_logger.query( _type=_type, min_time=min_time, max_time=max_time, conditions=conditions, admin_password=request.args["admin_password"] )








#######################
# Notifications       #
#######################

@app.route("/notifications/register", methods=["POST"])
def register():

    #Retrieve the token
    token = request.headers["Authorization"].replace("Bearer ", "")

    token_verification = serviceutils.verify_token(token)

    if 'error' in token_verification:

        serviceutils.log_event("could_not_register", {
                    "error": token_verification
                    })

        return token_verification

    uid = token_verification["uid"]

    serviceutils.log_event("successfully_registered", {
                    "uid": uid
                    })

    return notifs.register_device( request.form["platform"], request.form["device_id"], uid )




@app.route("/notifications/send", methods=["POST"])
def send():

    device_filter = request.form.get("device_filter") or "."
    platform = request.form.get("platform") or 0
    random_drop = request.form.get("random_drop") or 0

    notifs.send_notification( request.form["title"], request.form["message"], device_filter=device_filter, platform=platform, random_drop=random_drop, admin_password=request.form["admin_password"] )

    return "request pending"













if __name__ == '__main__':
    app.run(host='0.0.0.0')

    #Run tests
    auth.run_tests()
