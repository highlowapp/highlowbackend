import pymysql
import datetime

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

        cursor.execute("SELECT * FROM flags;")

        flags = cursor.fetchall()

        conn.commit()
        conn.close()

        return {
            "flags": flags
        }