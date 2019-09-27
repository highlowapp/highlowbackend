import pymysql
import datetime
import bleach

class Admin:
    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database

    def total_users(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users;")

        user_list = cursor.fetchall()

        conn.commit()
        conn.close()

        return {
            "total_users": len(user_list)
        }

    def get_flags(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM flags WHERE open=TRUE;")

        flags = cursor.fetchall()

        conn.commit()
        conn.close()

        return {
            "flags": flags
        }

    def dismiss_flag(self, flag_id):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        flag_id_str = pymysql.escape_string( bleach.clean(str(flag_id)) )

        cursor.execute("UPDATE flags SET open=false WHERE id={}".format(flag_id_str))

        conn.commit()
        conn.close()

        return {
            "status": "success"
        }