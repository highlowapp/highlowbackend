from flask import Flask, request
from User import User
import requests
import Helpers

app = Flask(__name__)

#MySQL credentials
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")

#Auth service
auth_service = Helpers.service("auth")

host = mysql_config["host"]
username = mysql_config["username"]
password = mysql_config["password"]
database = mysql_config["database"]

@app.route("/get/<string:property>", methods=["POST"])
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


@app.route("/set/<string:property>", methods=["POST"])
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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port='80')
