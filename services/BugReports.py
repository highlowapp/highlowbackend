import pymysql
import bleach
import json

class BugReports:
    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database
    def report_bug(self, uid, title, message):
        uid = pymysql.escape_string( bleach.clean(uid) )
        title = pymysql.escape_string( bleach.clean(title) )
        message = pymysql.escape_string( bleach.clean(message) )

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("INSERT INTO bug_reports(uid, title, message) VALUES('{}', '{}', '{}');".format(uid, title, message))

        conn.commit()
        conn.close()

        return json.dumps({"status": "success"})

    def dismiss(self, bug_id):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        bug_id = pymysql.escape_string( bleach.clean( str(bug_id) ) )

        cursor.execute("DELETE FROM bug_reports WHERE id='{}';".format(bug_id))

        conn.commit()
        conn.close()

        return { "status": "success" }

    def list_bugs(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM bug_reports;")

        bug_reports = cursor.fetchall()

        conn.commit()
        conn.close()

        for i in bug_reports:
            i["_timestamp"] = i["_timestamp"].isoformat()

        return {
            "bug_reports": bug_reports
        }

