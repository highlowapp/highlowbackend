from flask import Flask, request, jsonify
from flask_cors import CORS
import Helpers
import requests
import json
from services.Auth import Auth
from services.HLEmail import HLEmail
from services.User import User
from services.HighLow import HighLow, HighLowList, Comments
from services.EventLogger import EventLogger
from services.Notifications import Notifications
from services.Admin import Admin
from services.BugReports import BugReports
from services.Activities import Activities
import serviceutils
from urllib.parse import unquote
from werkzeug.contrib.fixers import ProxyFix
import os
import rook
import db
import re




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

#Create a comment instance
_comments = Comments(host, username, password, database)

#Instantiate HLEmail
email_config = Helpers.read_json_from_file("config/email_config.json")
hlemail = HLEmail(email_config["email"])



#Event Logger configuration
eventlogger_config = Helpers.read_json_from_file("config/eventlogger_config.json")



#Create an event logger instance
event_logger = EventLogger(host, username, password, database)

#Create and admin instance
admin = Admin(host, username, password, database)

#Create a bug reports instance
bug_reports = BugReports(host, username, password, database)

#Create an Activities instance
activities = Activities(host, username, password, database)


#Create a Notifications instance
notifs = Notifications(host, username, password, database)

#Rookout config
rookout_config = Helpers.read_json_from_file("config/rookout_config.json")



FEED_LIMIT = 10




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

def printr(val):
    print(val)
    return val


#Create flask app
app = Flask(__name__)
cors = CORS(app, resources={r"/admin/*": {"origins":"*"}})


#Proxies
NUM_PROXIES = 1

def get_remote_addr(request):
    x_forwarded_for = request.headers.getlist("X-Forwarded-For")[0]

    forward_list = x_forwarded_for.split(",")

    return forward_list[ -(NUM_PROXIES + 1) ]




#Define app routes
@app.route("/uptime_check", methods=["GET", "POST"])
def uptime_check():
    return "IS_UP"

#######################
# Authentication      #
#######################

#Sign_up
@app.route("/auth/sign_up", methods=["GET", "POST"])
def sign_up():

    if request.method == "POST":
        result = json.loads( auth.sign_up( request.form["firstname"], request.form["lastname"], request.form["email"], request.form["password"], request.form["confirmpassword"], request.form.get('is_android') ) )

        if "error" in result:

            serviceutils.log_event("sign_up_error", {
                        "error": result["error"]
                        })
        else:
            serviceutils.log_event("user_signed_up", {
                        "uid": result["uid"]
                        })

            #Upload profile picture...
            serviceutils.upload_default_profile_picture(result["uid"])



        return json.dumps( result )

    return sign_up_html

#Sign_in
@app.route("/auth/sign_in", methods=["GET", "POST"])
def sign_in():

    if request.method == "POST":

        result = json.loads( auth.sign_in( request.form["email"], request.form["password"] ) )

        if "error" in result:

            serviceutils.log_event("sign_in_error", {
                        "error": result["error"],
                        "ip": get_remote_addr(request)
                        })

        else:
            serviceutils.log_event("user_signed_in", {
                        "uid": result["uid"]
                        })

        return json.dumps( result )

    return sign_in_html


@app.route("/auth/oauth/sign_in", methods=["POST"])
def oauth_signin():
    provider_key = request.form.get('provider_key')
    provider_name = request.form.get('provider_name')
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    email = request.form.get('email')
    profileimage = request.form.get('profileimage')

    return auth.sign_in_with_oauth(provider_key, provider_name, firstname, lastname, email, profileimage, request.form.get('is_android'))

#Reset password
@app.route("/auth/password_reset/<string:reset_id>", methods=["GET", "POST"])
def password_reset(reset_id):


    if request.method == "POST":
        result = auth.reset_password( reset_id, request.form["password"], request.form["confirmpassword"] )

        if result["status"] == "success":

            serviceutils.log_event("user_reset_password", {
                        "reset_id": reset_id,
                        })

            return "Your password has been successfully reset!"

        else:

            serviceutils.log_event("error_in_reseting_password", {
                        "error": result["error"],
                        "ip": get_remote_addr(request)
                        })

            return "An error occurred when resetting your password. Try again."

    return reset_password_html

#Send password reset email
@app.route("/auth/forgot_password", methods=["POST"])
def forgot_password():

    return json.dumps( auth.send_password_reset_email( request.form["email"] ) )

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
                    "false_token": token,
                    "ip": get_remote_addr(request)
                    })

        return '{ "error": "' + result + '" }'

    #Otherwise, return the UID

    return '{ "uid": "' + result + '" }'


#Refresh access
@app.route("/auth/refresh_access", methods=["POST"])
def refresh_access():
    #Get the refresh token
    refresh_token = request.form["refresh"]

    #Refresh access
    result = auth.refresh_access(refresh_token)

    #Make sure there wasn't an error
    if result == "ERROR-INVALID-REFRESH-TOKEN":
        serviceutils.log_event("invalid_refresh_token", {
            "error": result,
            "false_token": refresh_token,
            "ip": get_remote_addr(request)
        })

        return '{"error": "' + result + '" }'

    #Otherwise, return the new access token
    return '{"access": "' + result + '"}'











#######################
# Email               #
#######################
@app.route("/email/send_email", methods=["POST"])
def send_email():
    return hlemail.send_email( request.form["email"], request.form["subject"], request.form["message"], request.form["password"] )











#######################
# User                #
#######################

@app.route("/user/get", methods=["POST"])
def get_complete_user():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification:
        return token_verification

    #Otherwise, get the user
    user = User(request.args.get("uid") or token_verification["uid"], host, username, password, database)


    #Create user JSON description
    user_json = {
        "uid": user.uid,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "profileimage": user.profileimage,
        "streak": user.calculate_streak(),
        "email": user.email,
        "bio": user.bio,
        "interests": user.interests
    }

    return json.dumps( user_json )

@app.route("/user/interests", methods=["GET"])
def get_interests():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    #Otherwise, get the user
    user = User(result["uid"], host, username, password, database)

    return json.dumps( user.get_interests() )

@app.route("/user/get/<string:property>", methods=["POST"])
def get(property):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    #Otherwise, get the user
    user = User(result["uid"], host, username, password, database)

    #Get the specified property
    prprty = None
    if property == "streak":
        prprty = user.calculate_streak()
    else:
        prprty = getattr(user, property)

    return '{ "' + property + '": "' + prprty + '"}'


@app.route("/user/set/<string:property>", methods=["POST"])
def set(property):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'


    #Otherwise, get the user
    user = User(result["uid"], host, username, password, database)

    if property not in ["profileimage", "streak", "password", "email"] :
        #Set the specified property
        user.set_column(property, request.form["value"])
    elif property == "profileimage":
        image = request.files.get("file")

        if not image:
            return '{"error":"no-file-uploaded"}'

        user.set_profileimage(image, result["uid"])
    else:
        return '{ "error": "not-allowed" }'
    return '{ "status": "success" }'

@app.route("/user/set_profile", methods=["POST"])
def set_user_profile():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    try:
        user = User(result["uid"], host, username, password, database)
    except:
        return '{"error": "user-no-exist"}'

    #Set all items
    profileimage = request.files.get("file")
    if profileimage:
        state = json.loads( user.set_profileimage(profileimage, result["uid"]) )
        if 'error' in state:
            return json.dumps(state)

    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    bio = request.form.get("bio")

    if firstname:
        user.set_column("firstname", firstname)
    if lastname:
        user.set_column("lastname", lastname)
    if bio:
        user.set_column("bio", bio)

    #Create user JSON description
    user_json = {
        "uid": user.uid,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "profileimage": user.profileimage,
        "streak": user.calculate_streak(),
        "email": user.email,
        "bio": user.bio,
        "interests": user.interests
    }

    return json.dumps( user_json )

@app.route("/user/flag/<string:_user>", methods=["POST"])
def doflag(_user):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    try:
        user = User(_user, host, username, password, database)
    except:
        return '{ "error": "user-no-exist" }'

    return user.flag(flagger)

@app.route("/user/unflag/<string:_user>", methods=["POST"])
def unflag(_user):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    try:
        user = User(_user, host, username, password, database)
    except:
        return '{ "error": "user-no-exist" }'

    return user.unflag(flagger)

@app.route("/user/feed/page/<int:page>", methods=["GET"])
def get_feed(page):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'


    uid = result["uid"]

    supports_html = request.args.get('supports_html') or False

    user = User(uid, host, username, password, database)
    return user.get_feed(FEED_LIMIT, page, supports_html=supports_html)


@app.route("/user/friends", methods=["GET"])
def get_friends():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'


    uid = request.args.get("uid") or result["uid"]


    user = User(uid, host, username, password, database)
    return json.dumps( user.list_friends() )

@app.route("/user/allFriends", methods=["GET"])
def new_get_friends():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = request.args.get("uid") or result["uid"]
    user = User(uid, host, username, password, database)
    return json.dumps( user.get_friends(result['uid']) )

@app.route("/user/<string:friend>/unfriend", methods=["POST"])
def unfriend(friend):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)

    return json.dumps( user.reject_friend(friend) )


@app.route("/user/<string:user_id>/request_friend", methods=["POST"])
def request_friend(user_id):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)
    return json.dumps( user.request_friend(user_id) )


@app.route("/user/search", methods=["POST"])
def search_users():
    ##Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    search = request.form["search"]

    user = User(uid, host, username, password, database)
    return user.search_friends(search)

@app.route("/user/get_pending_friendships", methods=["GET"])
def get_pending():
    ##Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)
    return user.list_pending_requests()



@app.route("/user/accept_friend/<string:friend>", methods=["POST"])
def accept_friendship(friend):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)

    return json.dumps( user.accept_friend(friend) )

@app.route("/user/calendar", methods=["GET"])
def get_calendar():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)

    return json.dumps( user.get_calendar() )

@app.route("/user/interests/create", methods=["POST"])
def create_interest():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)

    return json.dumps( user.create_interest(request.form.get('name')) )

@app.route("/user/interests/add", methods=["POST"])
def add_interest():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    interests = request.form.getlist('interests[]')


    user = User(uid, host, username, password, database)

    return json.dumps( user.add_interests(interests) )

@app.route("/user/interest/add", methods=["POST"])
def add_single_interest():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    interest = request.form.get('interest')


    user = User(uid, host, username, password, database)

    return json.dumps( user.add_interests([interest]) )


@app.route("/user/interests/remove", methods=["POST"])
def remove_interest():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    interests = request.form.getlist('interests[]')

    user = User(uid, host, username, password, database)

    return json.dumps( user.remove_interests(interests) )

@app.route("/user/interest/remove", methods=["POST"])
def remove_single_interest():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    interest = request.form.get('interest')

    user = User(uid, host, username, password, database)

    return json.dumps( user.remove_interests([interest]) )

@app.route("/user/interests/all", methods=["GET"])
def get_all_interests():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)

    return json.dumps( user.get_all_interests() )

@app.route("/user/friends/suggestions", methods=["GET"])
def get_friend_suggestions():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    result = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    uid = result["uid"]

    user = User(uid, host, username, password, database)

    return json.dumps( user.get_mutual_interests() )




#######################
# HighLow             #
#######################
@app.route("/highlow/set/high", methods=["POST"])
def sethigh():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    uid = verification["uid"]

    high = request.form.get("high")
    high_image = request.files.get("file")
    request_id = request.form.get('request_id')
    isPrivateStr = request.form.get("private")
    supports_html = request.form.get('supports_html') or False
    isPrivate = False

    if isPrivateStr in ['true', '1']:
        isPrivate = True

    highlow = None

    if "highlowid" in request.form:

        highlow = HighLow(host, username, password, database, high_low_id=request.form["highlowid"])
        return highlow.update_high(uid, text=high, image=high_image, isPrivate=isPrivate, supports_html=supports_html)


    else:
        highlow = HighLow(host, username, password, database)
        return highlow.create(uid, request.form["date"], high=high, low=None, high_image=high_image, low_image=None, isPrivate=isPrivate, request_id=request_id, supports_html=supports_html)




@app.route("/highlow/set/low", methods=["POST"])
def setlow():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    uid = verification["uid"]

    low = request.form.get("low")
    low_image = request.files.get("file")
    request_id = request.form.get('request_id')
    supports_html = request.form.get('supports_html') or False
    isPrivateStr = request.form.get("private")
    isPrivate = False

    if isPrivateStr in ['true', '1']:
        isPrivate = True

    highlow = None


    if "highlowid" in request.form:

        highlow = HighLow(host, username, password, database, high_low_id=request.form["highlowid"])
        return highlow.update_low(uid, text=low, image=low_image, isPrivate=isPrivate, supports_html=supports_html)



    else:

        highlow = HighLow(host, username, password, database)
        return highlow.create(uid, request.form["date"], high=None, low=low, high_image=None, low_image=low_image, isPrivate=isPrivate, request_id=request_id, supports_html=supports_html)


@app.route("/highlow/<string:highlowid>/private/<int:on>", methods=["GET"])
def toggle_private(highlowid, on):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    uid = verification["uid"]

    supports_html = request.args.get('supports_html') or False

    highlow = HighLow(host, username, password, database, high_low_id=highlowid)

    if on == 1:
        return highlow.make_private(uid, supports_html=supports_html)
    else:
        return highlow.make_public(uid, supports_html=supports_html)


@app.route("/highlow/like/<string:highlowid>", methods=["POST"])
def like(highlowid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )
    else:
        uid = verification["uid"]

        try:
            highlow = HighLow(host, username, password, database, highlowid)

            result = highlow.like(uid)

            return json.dumps( result )
        except Exception:
            return '{"error":"invalid-highlowid"}'


@app.route("/highlow/unlike/<string:highlowid>", methods=["POST"])
def unlike(highlowid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )
    else:
        uid = verification["uid"]

        highlow = HighLow(host, username, password, database, highlowid)
        result = highlow.unlike(uid)

        return result






@app.route("/highlow/comment/<string:highlowid>", methods=["POST"])
def comment(highlowid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    else:
        uid = verification["uid"]

        message = request.form.get("message") or ""
        request_id = request.form.get('request_id')


        highlow = HighLow(host, username, password, database, highlowid)
        result = highlow.comment(uid, message, request_id=request_id)

        return json.dumps( { "comments": result } )


@app.route("/highlow/get/today", methods=["GET"])
def get_today():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    else:
        uid = verification["uid"]

        supports_html = request.args.get('supports_html') or False

        #Now, we use `HighLowList` to get today's highlow
        highlowlist = HighLowList(host, username, password, database)

        today_highlow = highlowlist.get_today_for_user(uid, supports_html=supports_html)

        return json.dumps(today_highlow)

@app.route("/highlow/<string:highlowid>", methods=["GET"])
def get_arbitrary(highlowid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")
    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )
    else:

        try:
            supports_html = request.args.get('supports_html') or False
            highlow = HighLow(host, username, password, database, highlowid)
            return json.dumps( highlow.get_json(verification["uid"], supports_html=supports_html) )
        except Exception as e:
            return '{ "error": "invalid-highlowid"  }'



@app.route("/highlow/get/user/page/<int:page>", methods=["GET"])
def get_user(page):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    else:
        #Defaults to the current user
        uid = request.args.get("uid") or verification["uid"]
        supports_html = request.args.get('supports_html') or False

        highlowlist = HighLowList(host, username, password, database)

        highlows = highlowlist.get_highlows_for_user(uid, verification["uid"], FEED_LIMIT, page, sortby=request.args.get("sortby"), supports_html=supports_html )

        return '{ "highlows": ' + json.dumps( highlows ) + ' }'


@app.route("/highlow/get/date", methods=["POST"])
def get_date():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    date = request.form["date"]
    supports_html = request.form.get('supports_html') or False

    highlowlist = HighLowList(host, username, password, database)

    return json.dumps( highlowlist.get_day_for_user(verification["uid"], date, verification["uid"], supports_html=supports_html) )







@app.route("/highlow/flag/<string:highlowid>", methods=["POST"])
def flaghighlow(highlowid):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    try:
        supports_html = request.form.get('supports_html') or False
        highlow = HighLow(host, username, password, database, high_low_id=highlowid)
    except:
        return '{ "error": "highlow-no-exist" }'

    return highlow.flag(flagger, supports_html=supports_html)


@app.route("/highlow/unflag/<string:highlowid>", methods=["POST"])
def unflaghighlow(highlowid):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)


    #Obtain the result as JSON
    result = token_verification_request

    #If there was an error, return the error
    if "error" in result:
        return '{ "error": "' + result["error"] + '" }'

    flagger = result["uid"]

    supports_html = request.form.get('supports_html') or False

    highlow = HighLow(host, username, password, database, high_low_id=highlowid)

    return highlow.unflag(flagger, supports_html=supports_html)




@app.route("/highlow/get_comments/<string:highlowid>", methods=["GET"])
def get_comments(highlowid):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification_request:
        return '{ "error": "' + token_verification_request["error"] + '" }'

    try:
        highlow = HighLow(host, username, password, database, high_low_id=highlowid)
    except:
        return '{ "error": "highlow-no-exist" }'

    return json.dumps( { "comments": highlow.get_comments() } )



@app.route("/comment/delete/<string:commentid>", methods=["POST"])
def delete_comment(commentid):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification_request:
        return '{ "error": "' + token_verification_request["error"] + '" }'

    _comments.delete_comment(token_verification_request["uid"], commentid)

    return '{"status":"success"}'

@app.route("/comment/update/<string:commentid>", methods=["POST"])
def update_comment(commentid):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification_request:
        return '{ "error": "' + token_verification_request["error"] + '" }'

    return _comments.update_comment(token_verification_request["uid"], commentid, request.form.get("message"))






########################
# Activities           #
########################

@app.route('/user/activities/<string:activity_id>', methods=['GET', 'POST', 'DELETE'])
def individual_activity(activity_id):
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    if request.method == 'GET':
        return json.dumps( activities.get_by_id(uid, activity_id) )

    if request.method == 'POST':
        return json.dumps( activities.update(uid, activity_id, request.form.get('data')))

    if request.method == 'DELETE':
        return json.dumps( activities.delete(uid, activity_id) )

@app.route('/user/<string:uid>/activities', methods=['GET'])
def user_activities(uid):
    viewer, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    if request.method == 'GET':
        return json.dumps( activities.get_for_user(uid, viewer, request.args.get('page')) )

@app.route('/user/diaryEntries', methods=['GET'])
def get_diaryEntries():
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return  error

    return json.dumps( activities.get_diary_entries(uid, request.args.get('page')) )

@app.route('/user/activities', methods=['POST'])
def add_activity():
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    if request.method == 'POST':
        return json.dumps( activities.add(uid, request.form.get('type'), request.form.get('data'), request.form.get('date')) )

@app.route('/user/activities/<string:activity_id>/sharing', methods=['GET', 'POST'])
def sharing(activity_id):
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    if request.method == 'GET':
        return json.dumps( activities.get_sharing_policy(uid, activity_id) )
    if request.method == 'POST':
        return json.dumps( activities.set_sharing_policy(uid, activity_id, category=request.form.get('category'), uids=request.form.getlist('uids[]')) )

@app.route('/user/activities/<string:activity_id>/comments', methods=['POST'])
def comment_on_activity(activity_id):
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    return json.dumps( activities.comment(uid, activity_id, request.form.get('message')) )

@app.route('/comments/<string:commentid>', methods=['POST', 'DELETE'])
def change_comment(commentid):
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    if request.method == 'POST':
        return json.dumps( activities.update_comment(uid, commentid, request.form.get('message')) )
    if request.method == 'DELETE':
        return json.dumps( activities.delete_comment(uid, commentid) )

@app.route('/user/<string:uid>/activities/chart', methods=['GET'])
def get_activity_chart(uid):
    viewer, error = serviceutils.get_current_user(request)
    if error is not None:
        return error
    return json.dumps( activities.get_activity_chart(uid) )

@app.route('/user/activities/<string:activity_id>/flag', methods=['POST', 'DELETE'])
def flag_activity(activity_id):
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    if request.method == 'POST':
        return json.dumps( activities.flag(uid, activity_id) )
    if request.method == 'DELETE':
        return json.dumps( activities.unflag(uid, activity_id) )

@app.route('/user/activities/<string:activity_id>/like', methods=['POST', 'DELETE'])
def like_activity(activity_id):
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error
    
    if request.method == 'POST':
        return json.dumps( activities.like(uid, activity_id) )
    if request.method == 'DELETE':
        return json.dumps( activities.unlike(uid, activity_id) )

@app.route('/user/newFeed/page/<int:page>', methods=['GET'])
def get_new_feed(page):
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    return json.dumps( activities.get_new_feed(uid, page) )

@app.route('/user/activities/addImage', methods=['POST'])
def add_activity_image():
    image = request.files.get("file")
    if image is None:
        return '{ "error": "no-file-found" }'
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error

    return activities.add_image(uid, image)

@app.route('/user/activities/uploadAudio', methods=['POST'])
def upload_audio():
    audio = request.files.get("file")
    if audio is None:
        return '{ "error": "no-file-found" }'
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error
    return activities.upload_audio(uid, audio)

@app.route('/user/isLoggedIn', methods=['GET'])
def isLoggedIn():
    uid, error = serviceutils.get_current_user(request)
    if error is not None:
        return error
    return json.dumps({ 'uid': uid })


#######################
# EventLogger         #
#######################

#Create the `log_event` route
@app.route("/eventlogger/log_event", methods=["POST"])
def log_event():

    if request.form.get("admin_password") != eventlogger_config["admin_password"]:
        serviceutils.log_event("eventlogger_failed_attempt", {
            "ip": get_remote_addr(request)
            })

    return event_logger.log_event( request.form["event_type"], request.form["data"], request.form["admin_password"] )


@app.route("/eventlogger/query", methods=["GET"])
def query():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    _type = request.args.get("type")
    min_time = request.args.get("min_time")
    max_time = request.args.get("max_time")

    conditions_raw = request.args.get("conditions")
    conditions = None
    if conditions_raw:
        conditions_json_str = unquote(conditions_raw)


        conditions = json.loads( conditions_json_str )

    query_result = event_logger.query( _type=_type, min_time=min_time, max_time=max_time, conditions=conditions or [], admin_password=request.args["admin_password"] )

    response = jsonify(query_result)

    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response


## ADMIN
@app.route("/admin/sign_in", methods=["POST"])
def admin_sign_in():
    result = json.loads( auth.admin_sign_in( request.form["username"], request.form["password"] ) )
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST')
    return response

@app.route("/admin/refresh_access", methods=["POST"])
def admin_refresh_access():
    #Get the refresh token
    refresh_token = request.form["refresh"]

    #Refresh access
    result = auth.refresh_admin_access(refresh_token)

    response = jsonify(result)

    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response



@app.route("/admin/total_users", methods=["GET"])
def total_users():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    query_result = admin.total_users()

    response = jsonify(query_result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/list_flags", methods=["GET"])
def get_flags():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    query_result = admin.get_flags()

    response = jsonify(query_result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/inspect_user/<string:uid>", methods=["GET"])
def inspect_user(uid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    #Otherwise, get the user
    user = User(uid, host, username, password, database)


    #Create user JSON description
    user_json = {
        "uid": user.uid,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "profileimage": user.profileimage,
        "streak": user.calculate_streak(),
        "email": user.email,
        "bio": user.bio,
        "times_flagged": user.times_flagged,
        "banned": user.banned
    }

    response = jsonify(user_json)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/ban/<string:uid>", methods=["GET"])
def ban_user(uid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    #Otherwise, get the user
    user = User(uid, host, username, password, database)

    result = user.ban()

    response = jsonify(result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response


@app.route("/admin/unban/<string:uid>", methods=["GET"])
def unban_user(uid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    #Otherwise, get the user
    user = User(uid, host, username, password, database)

    result = user.unban()

    response = jsonify(result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response


@app.route("/admin/inspect_highlow/<string:highlowid>", methods=["GET"])
def inspect_highlow(highlowid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    highlow = HighLow(host, username, password, database, highlowid)
    result = highlow.get_json()

    response = jsonify(result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/delete_highlow/<string:highlowid>", methods=["GET"])
def delete_highlow(highlowid):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    highlow = HighLow(host, username, password, database, highlowid)
    highlow.delete()

    response = jsonify({ "status": "success" })
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/dismiss_flag/<int:flag_id>", methods=["GET"])
def dismissFlag(flag_id):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    result = admin.dismiss_flag(flag_id)

    response = jsonify(result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/dismiss_bug/<int:bug_id>", methods=["GET"])
def dismiss_bug(bug_id):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    result = bug_reports.dismiss(bug_id)

    response = jsonify(result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/list_bug_reports", methods=["GET"])
def list_bug_reports():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    result = bug_reports.list_bugs()

    response = jsonify(result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response

@app.route("/admin/take_analytics_snapshot", methods=["GET"])
def take_analytics_snapshot():
    if request.args.get("admin_password") != eventlogger_config["admin_password"]:
        return "error"

    return admin.take_analytics_snapshot()

@app.route("/admin/get_analytics/<int:num_days>", methods=["GET"])
def get_analytics(num_days):
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    query_result = admin.get_analytics(num_days)

    response = jsonify(query_result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response


@app.route("/admin/createCompanyHighLow", methods=["POST"])
def createCompanyHighLow():
    #Verify auth token
    token = request.headers["Authorization"].replace("Bearer ", "")

    verification = serviceutils.verify_admin_token(token)

    if 'error' in verification:
        return json.dumps( verification )

    high = request.form.get('high')
    low = request.form.get('low')
    high_image = request.files.get('high_image')
    low_image = request.files.get('low_image')
    date = request.form.get('date')

    result = admin.create_company_highlow(verification['user'], high, low, high_image, low_image, date)

    response = jsonify(result)
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST')

    return response


@app.route("/bug_reports/submit", methods=["POST"])
def report_bug():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification_request:
        return '{ "error": "' + token_verification_request["error"] + '" }'

    return bug_reports.report_bug(token_verification_request["uid"], request.form["title"], request.form["message"])








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

@app.route("/notifications/deregister/<string:device_id>", methods=["POST"])
def deregister(device_id):
    #Retrieve the token
    token = request.headers["Authorization"].replace("Bearer ", "")

    # Because it's not that big of a deal for someone to be able to deregister
    # another user's device from push notifications, we accept old tokens.
    # It's unlikely that even an old token would be obtained by someone.
    # It's more critical that we make sure the users deregister their device before logging out.
    token_verification = serviceutils.verify_token_accept_old(token)

    if 'error' in token_verification:
        return token_verification

    uid = token_verification["uid"]

    notifs.deregister_device(device_id, uid)

    return '{"status": "success"}'



@app.route("/notifications/send", methods=["POST"])
def send():

    device_filter = request.form.get("device_filter") or ".+"
    platform = request.form.get("platform") or 0
    random_drop = request.form.get("random_drop") or 0

    notifs.send_notification( request.form["title"], request.form["message"], device_filter=device_filter, platform=platform, random_drop=random_drop, admin_password=request.form["admin_password"] )

    return "request pending"

@app.route("/notifications/settings", methods=["GET"])
def get_notif_settings():
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification_request:
        return '{ "error": "' + token_verification_request["error"] + '" }'

    user = User(token_verification_request['uid'], host, username, password, database)
    return json.dumps( user.get_notif_settings() )

@app.route("/notifications/<string:setting>/on", methods=["POST"])
def turn_notif_setting_on(setting):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification_request:
        return '{ "error": "' + token_verification_request["error"] + '" }'

    try:
        user = User(token_verification_request['uid'], host, username, password, database)
        result = user.set_notif_setting(setting, True)

        return json.dumps(result)
    except:
        return '{ "error": "invalid-setting" }'

@app.route("/notifications/<string:setting>/off", methods=["POST"])
def turn_notif_setting_off(setting):
    #Get token from Authorization
    token = request.headers["Authorization"].replace("Bearer ", "")

    #Make a request to the Auth service
    token_verification_request = serviceutils.verify_token(token)

    #If there was an error, return the error
    if "error" in token_verification_request:
        return '{ "error": "' + token_verification_request["error"] + '" }'

    try:
        user = User(token_verification_request['uid'], host, username, password, database)
        result = user.set_notif_setting(setting, False)

        return json.dumps(result)
    except:
        return '{ "error": "invalid-setting" }'


TAG_RE = re.compile(r'<[^>]+>')

def remove_tags(text):
    return TAG_RE.sub('', text)


##Data Migration
@app.route('/checkNewHighLows', methods=["GET"])
def checkNewHighLows():
    given_password = request.args['password']
    correct_password = eventlogger_config['admin_password']
    if given_password != correct_password:
        return '{ "error": "access-denied" }'

    working_db = db.DB(host, username, password, database)

    highlows = working_db.get_all('get_missing_highlows')

    for highlow in highlows:
        #activity_id, uid, type, timestamp, data, date, title
        activity_id = highlow['highlowid']
        uid = highlow['uid']
        _type = 'highlow'
        date = highlow['_date']
        timestamp = highlow['_timestamp']

        year = date[0:4]
        month = date[5:7]
        day = date[8:10]

        title = "{}/{}/{}".format(month, day, year)

        high = 'No content provided'
        if highlow['high'] is not None and len(highlow['high']) > 0:
            high = remove_tags(highlow['high'])

        low = 'No content provided'
        if highlow['low'] is not None and len(highlow['low']) > 0:
            low = remove_tags(highlow['low'])
        
        data = {
            'title': title,
            'type': 'highlow',
            'blocks': [
                {
                    'type': 'h1',
                    'content': 'High',
                    'editable': False
                },
                {
                    'type': 'img',
                    'src': 'https://storage.googleapis.com/highlowfiles/highs/' + highlow['high_image'] if highlow['high_image'] is not None else '',
                    'editable': True
                },
                {
                    'type': 'p',
                    'content': high,
                    'editable': True
                },
                {
                    'type': 'h1',
                    'content': 'Low',
                    'editable': False
                },
                {
                    'type': 'img',
                    'src': 'https://storage.googleapis.com/highlowfiles/lows/' + highlow['low_image'] if highlow['low_image'] is not None else '',
                    'editable': True
                },
                {
                    'type': 'p',
                    'content': low,
                    'editable': True
                }
            ]
        }

        working_db.execute('add_full_activity', activity_id, uid, title, _type, timestamp, json.dumps(data), date)
        
        if highlow['private'] == 0:
            working_db.execute('set_sharing_policy', activity_id, 'all')

    comments = working_db.get_all('get_missing_highlow_comments')

    for comment in comments:
        commentid = comment['commentid']
        activity_id = comment['highlowid']
        uid = comment['uid']
        message = comment['message']
        timestamp = comment['_timestamp']

        working_db.execute('add_full_activity_comment', commentid, activity_id, uid, message, timestamp)

    working_db.commit_and_close()

    return '{"status": "success"}'

    



rook.start(token=rookout_config['token'])

if __name__ == '__main__':
    app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=3)
    app.run(host='0.0.0.0')
