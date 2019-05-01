import pymysql
import bleach
import Helpers
import json
import firebase_admin
import random

#Admin password
notifications_config = Helpers.read_json_from_file("config/notifications_config.json")
ADMIN_PASSWORD = notifications_config["admin_password"]

#Initialize firebase app
firebase_app = firebase_admin.initialize_app()



class Notifications:

    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database


    def register_device(self, platform, device_id, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor)
        cursor = conn.cursor()

        platform = bleach.clean(platform)
        device_id = bleach.clean(device_id)
        uid = bleach.clean(uid)

        cursor.execute( "INSERT INTO devices(device_id, uid, platform) VALUES('{}', '{}', {});".format(device_id, uid, platform) )

        conn.commit()
        conn.close()

        return json.dumps( { "device_id": device_id, "uid": uid, "platform": platform } )

    def send_notification(self, title, message, device_filter=".", platform=0, random_drop=0, admin_password=""):
        device_list = []

        platform = bleach.clean(platform)

        query = "SELECT * FROM devices WHERE device_id REGEXP '{}'"

        if platform > 0:
            query += " AND platform=" + platform + ";"

        else:
            query += ";"

        if admin_password != ADMIN_PASSWORD:
            return json.dumps( { "error": "incorrect-password"} )

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor)
        cursor = conn.cursor()

        cursor.execute(query)

        devices = cursor.fetchall()

        for i in devices:
            if random.random() > random_drop:
                device_list.append(i["device_id"])

        push_notification = firebase_admin.messaging.Message(
            notification=firebase_admin.messaging.Notification(title=title, body=message)
        )

        response = firebase_admin.messaging.send(push_notification)

        #Future - log the response?

        conn.commit()
        conn.close()