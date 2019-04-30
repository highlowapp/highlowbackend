from flask import Flask, request
from HighLow import HighLow
from HighLowList import HighLowList
import requests 
import Helpers
import json

#Create a Flask app instance
app = Flask(__name__)

#MySQL credentials
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")

host = mysql_config["host"]
username = mysql_config["username"]
password = mysql_config["password"]
database = mysql_config["database"]




@app.route("/set/<string:highlowid>", methods=["POST"])
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


	
    




@app.route("/like/<string:highlowid>", methods=["POST"])
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


@app.route("/comment/<string:highlowid>", methods=["POST"])
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
@app.route("/get/today", methods=["GET"])
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


@app.route("/get/user", methods=["GET"])
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

#Run the app
if __name__ == '__main__':
  app.run(debug=True)

