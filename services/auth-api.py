import os
from flask import Flask, session, request
from Auth import Auth
import Helpers

#MySQL server configuration
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")

#Auth service
auth_service = Helpers.service("auth")

#Create an Auth instance
auth = Auth(auth_service, mysql_config["host"], mysql_config["username"], mysql_config["password"], mysql_config["database"])

#Create a Flask app instance
app = Flask(__name__)


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


#Define app routes

@app.route("/", methods=["GET", "POST"])
def main_page():

    return "Go somewhere else"

#######################
# Authentication      #
#######################

#Sign_up
@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():

    if request.method == "POST":

        return auth.sign_up( request.form["firstname"], request.form["lastname"], request.form["email"], request.form["password"], request.form["confirmpassword"] )
    
    return sign_up_html





#Sign_in
@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():

    if request.method == "POST":

        return auth.sign_in( request.form["email"], request.form["password"] )

    return sign_in_html





#Reset password
@app.route("/password_reset/<string:reset_id>", methods=["GET", "POST"])
def password_reset(reset_id):
    
    if request.method == "POST":
        
        return auth.reset_password( reset_id, request.form["password"], request.form["confirmpassword"] )

    return reset_password_html





#Send password reset email
@app.route("/forgot_password", methods=["POST"])
def forgot_password():
    
    return auth.send_password_reset_email( request.form["email"] )


#Verify token
@app.route("/verify_token", methods=["GET", "POST"])
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
@app.route("/blacklist/<string:token>", methods=["GET", "POST"])
def blacklist_token(token):
    auth.blacklist_token(token)
    return '{"status":"success"}'



#Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port="80", debug=True)
