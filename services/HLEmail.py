from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class HLEmail:
	def __init__(self, sender):
		self.sender = sender


	#The function that sends the email
	def send_email(self, receiver, subject, message, admin_password):
		msg = Mail(
		from_email=self.sender,
		to_emails=receiver,
		subject=subject,
		html_content=message
		)

		try:
			sg = SendGridAPIClient(admin_password)
			response = sg.send(msg)

			return '{"status": "success"}'
		except Exception as e:
			return '{"status": "failure"}'
