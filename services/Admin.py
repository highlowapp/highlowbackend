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

    def take_analytics_snapshot(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        num_users = 0

        cursor.execute("SELECT COUNT(*) AS num_users FROM users;")

        row = cursor.fetchone()

        num_users = row['num_users']

        cursor.execute("SELECT COUNT(*) AS num_oauth_users FROM (SELECT * FROM oauth_accounts GROUP BY uid) AS unique_oauth;")

        num_oauth_accounts = 0

        row = cursor.fetchone()

        num_oauth_accounts = row['num_oauth_users']

        cursor.execute("SELECT SUM(status=2) AS num_friendships FROM friends;")
        row = cursor.fetchone()
        num_friendships = row['num_friendships']

        cursor.execute("SELECT COUNT(*) AS num_highlows FROM highlows;")
        row = cursor.fetchone()
        num_highlows = row['num_highlows']

        cursor.execute("INSERT INTO analytics(num_users, num_oauth_users, num_friendships, num_highlows) VALUES({}, {}, {}, {});".format(num_users, num_oauth_accounts, num_friendships, num_highlows))

        conn.commit()
        conn.close()

        return '{"status": "success"}'

    def get_analytics(self, num_days):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM analytics ORDER BY date DESC LIMIT {};".format(num_days))

        analytics = cursor.fetchall()

        conn.commit()
        conn.close()

        for snapshot in analytics:
            snapshot['date'] = snapshot['date'].isoformat()

        return {
            "analytics": analytics
        }
