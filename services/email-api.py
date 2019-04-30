from flask import Flask, request
from HLEmail import HLEmail
import Helpers

#Create app instance
app = Flask(__name__)

#Instantiate HLEmail
email_config = Helpers.read_json_from_file("config/email_config.json")
hlemail = HLEmail(email_config["email"])

@app.route("/send_html_email", methods=["POST"])
def send_html_email():
	hlemail.send_html_email( request.form["email"], request.form["message"], request.form["password"] )

@app.route("/send_email", methods=["POST"])
def send_email():
	hlemail.send_email( request.form["email"], request.form["message"], request.form["password"] )

if __name__ == '__main__':
	app.run(host="0.0.0.0", port="80")
