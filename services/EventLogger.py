import pymysql
import bleach
import json
import datetime
import Helpers

eventlogger_config = Helpers.read_json_from_file("config/eventlogger_config.json")

_admin_password = eventlogger_config["admin_password"]


class EventLogger:
    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database

    def log_event(self, event_type, data, admin_password =""):

        if admin_password != _admin_password:
            return '{"error": "not-authorized"}'

        #Clean the type and the data
        event_type = bleach.clean(event_type)
        data = bleach.clean( json.dumps(data) )

        #Get the timestamp
        timestamp = datetime.datetime.now().timestamp()

        #Connect to MySQL database
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor)
        cursor = conn.cursor()

        #Insert a new row
        cursor.execute("INSERT INTO events(type, data, timestamp) VALUES('" + event_type + "', '" + data + "', " + timestamp + ");")

        #Commit and close the connection
        conn.commit()
        conn.close()

        return ""

    def query(self, _type=None, min_time=None, max_time=None, conditions=[], admin_password=""):

        #Data condition constraints
        condition_str = ""

        for i in conditions:
            path = i["path"]
            operator = i["operator"]
            value = i["value"]

            condition_str += " AND JSON_EXTRACT(data, '{}') {} {} ".format(path, operator, value)


        #Time constraint
        time_constraint_str = ""

        if min_time != None:
            time_constraint_str += " AND _timestamp >= TIMESTAMP('{}') ".format(min_time)

        if max_time != None:
            time_constraint_str += " AND _timestamp <= TIMESTAMP('{}') ".format(max_time)
        

        #Type constraint
        type_str = ""

        if _type != None:
            type_str += " AND type='{}'".format(_type)

        #Password check
        if admin_password != _admin_password:
            return '{"error":"not-authorized"}'

        sql_statement = "SELECT * FROM events WHERE 1=1 {} {} {} ORDER BY _timestamp DESC;".format(condition_str, time_constraint_str, type_str)

        #Connect to MySQL database
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor)
        cursor = conn.cursor()

        #Get the appropriate data by executing the SQL statement
        cursor.execute(sql_statement)

        #Unpack the data
        data = cursor.fetchall()

        #Commit and close the connection
        conn.commit()
        conn.close()

        #Return the data
        return json.dumps(data)
