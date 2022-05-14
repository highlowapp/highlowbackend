import pymysql
import requests
import uuid
import time
import datetime
import bleach
import json
from services.FileStorage import FileStorage
from services.Notifications import Notifications
from services.User import User
from bs4 import BeautifulSoup

VALID_HTML_TAGS = ['strong', 'em', 'b', 'i', 'a', 'p', 'div', 'span', 'ul', 'li', 'br', 'strike', 's', 'blockquote']

class HighLow:

    def __init__(self, host, username, password, database, high_low_id=None):
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.high_low_id = ""

        if high_low_id is not None:
            self.high_low_id = pymysql.escape_string( bleach.clean(high_low_id) )

            conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
            cursor = conn.cursor()
            cursor.execute( "SELECT * FROM highlows WHERE highlowid='{}';".format(self.high_low_id) )
            result = cursor.fetchone()
            conn.commit()
            conn.close()

            if not result:
                raise ValueError("highlow-no-exist")
            
            self.uid = result["uid"]
            self.high = result["high"]
            self.low = result["low"]
            self.high_image = result["high_image"]
            self.low_image = result["low_image"]
            self.timestamp = result["_timestamp"]
            self.total_likes = result["total_likes"]
            self.date = result["_date"]
            self.isPrivate = result["private"] == 1
        else:
            self.high = ""
            self.low = ""
            self.high_image = ""
            self.low_image = ""
            self.timestamp = None
            self.total_likes = 0
            self.isPrivate = False
        self.protected_columns = []

    def sanitize_html(self, value):
        soup = BeautifulSoup(value)

        for tag in soup.findAll(True):
            if tag.name not in VALID_HTML_TAGS:
                tag.hidden = True

        return soup.renderContents().decode('utf-8')

    def create(self, uid, _date, high=None, low=None, high_image=None, low_image=None, isPrivate=False, request_id=None, supports_html=False):
        ## Create a new High/Low entry in the database ##

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Check to see if this is a duplicate request. If it is, return the original response
        if request_id is not None:
            request_id = pymysql.escape_string( bleach.clean(request_id) )
            cursor.execute("SELECT * FROM onetime_requests WHERE request_id='{}';".format(request_id))

            duplicate = cursor.fetchone()

            if duplicate is not None:
                return duplicate['response']

        _date = pymysql.escape_string( bleach.clean(_date) )

        cursor.execute("SELECT * FROM highlows WHERE uid='{}' AND _date='{}';".format(uid, _date))

        possible_duplicate = cursor.fetchone()

        if possible_duplicate is not None:
            self.high_low_id = possible_duplicate["highlowid"]
            self.date = _date
            self.high_image = possible_duplicate["high_image"]
            self.low_image = possible_duplicate["low_image"]
            self.high = possible_duplicate["high"]
            self.low = possible_duplicate["low"]
            self.uid = possible_duplicate["uid"]
            self.total_likes = possible_duplicate["total_likes"]
            self.timestamp = possible_duplicate["_timestamp"]
            self.isPrivate = possible_duplicate["private"] == 1
            conn.commit()
            conn.close()
            return self.update(uid, high, low, high_image, low_image, isPrivate)


        #Create a High/Low ID
        self.high_low_id = str( uuid.uuid1() )

        if high is not None:
            self.high = pymysql.escape_string( self.sanitize_html(high) )


            self.high = "{}".format(self.high)

        if low is not None:
            self.low = pymysql.escape_string( self.sanitize_html(low) )
            self.low = "{}".format(self.low)

        if high_image is not None:
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_high_images(high_image) )

            if 'error' in upload_result:
                conn.commit()
                conn.close()
                return json.dumps( upload_result )
        
            self.high_image = "{}".format(upload_result["file"])

        if low_image is not None:
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_low_images(low_image) )

            if 'error' in upload_result:
                conn.commit()
                conn.close()
                return json.dumps( upload_result )
        
            self.low_image = "{}".format(upload_result["file"])

        self.isPrivate = isPrivate

        _date = pymysql.escape_string( bleach.clean(_date) )

        self.date = _date

        self.uid = uid

        #Now, insert the data
        cursor.execute("INSERT INTO highlows(highlowid, uid, high, low, high_image, low_image, total_likes, _date, private) VALUES('{}', '{}', {}, {}, {}, {}, 0, '{}', {});".format(self.high_low_id, uid, "'{}'".format(self.high) if self.high else "NULL", "'{}'".format(self.low) if self.low else "NULL", "'{}'".format(self.high_image) if self.high_image else "NULL", "'{}'".format(self.low_image) if self.low_image else "NULL", self.date, "TRUE" if self.isPrivate else "FALSE") )

        #...and update the streak
        cursor.execute("UPDATE users SET streak = streak + 1 WHERE uid='{}';".format(uid))

        cursor.execute("SELECT _timestamp FROM highlows WHERE highlowid='{}';".format(self.high_low_id))

        self.timestamp = cursor.fetchone()["_timestamp"]

        #Commit and close the connection
        conn.commit()
        conn.close()

        if not self.isPrivate:
            try:
                user = User(uid, self.host, self.username, self.password, self.database)

                
                uids = user.get_friend_uids()

                notifs = Notifications(self.host, self.username, self.password, self.database)

                try:
                    notifs.send_notification_to_users("New Feed Item", user.firstname + " " + user.lastname + " created a new High/Low!", uids, 2, data={"highlowid": self.high_low_id})
                except:
                    pass
                """
                for other_uid in uids:
                    try:
                        friend = User(other_uid, self.host, self.username, self.password, self.database)
                        if friend.notify_new_feed_item:
                            notifs.send_notification_to_user("New Feed Item", user.firstname + " " + user.lastname + " created a new High/Low!", other_uid, data={"highlowid": self.high_low_id})
                    except: 
                        continue
                """
            except:
                pass

        #Return the HighLow ID
        response = json.dumps( self.get_json(uid=self.uid, supports_html=supports_html) )

        
        #If a request ID was given, store it in the onetime requests table
        if request_id is not None:
            request_id = pymysql.escape_string( bleach.clean(request_id) )
            #Connect to MySQL
            conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO onetime_requests(request_id, response) VALUES('{}', '{}');".format(request_id, response))
            conn.commit()
            conn.close()

        return response



    def get_json(self, uid=None, supports_html=False):
        json_object = {
            "uid": self.uid,
            "high": self.high,
            "low": self.low, 
            "high_image": self.high_image,
            "low_image": self.low_image,
            "total_likes": self.total_likes,
            "highlowid": self.high_low_id,
            "_timestamp": self.timestamp.isoformat(),
            "_date": self.date,
            "comments": [],
            "private": self.isPrivate
        }

        if not supports_html:
            if json_object['high'] is not None:
                json_object['high'] = self.html_to_plain_text(json_object['high'])
            if json_object['low'] is not None:
                json_object['low'] = self.html_to_plain_text(json_object['low'])

        if (uid != self.uid) and self.isPrivate:
            return { "error": "not-authorized" }

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        if uid is not None:
            cursor.execute( "SELECT * FROM likes WHERE uid='{}' AND highlowid='{}'".format(uid, self.high_low_id) )
            if cursor.fetchone() is not None:
                json_object["liked"] = True
            cursor.execute("SELECT * FROM flags WHERE uid='{}' AND highlowid='{}'".format(uid, self.high_low_id))
            if cursor.fetchone() is not None:
                json_object["flagged"] = True

        cursor.execute( """
            SELECT
                comments.highlowid AS highlowid,
                commentid,
                comments.uid AS uid,
                message,
                _timestamp,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage
            FROM
                `comments`
                JOIN users ON users.uid = comments.uid
            WHERE comments.highlowid = '{}' ORDER BY _timestamp;
            """.format(self.high_low_id) )

        comments = cursor.fetchall()

        conn.commit()
        conn.close()

        for i in range( len(comments) ):
            json_object["comments"].append(comments[i])
            json_object["comments"][i]["_timestamp"] = json_object["comments"][i]["_timestamp"].isoformat()

        return json_object

    def make_private(self, uid, supports_html=False):
        if uid != self.uid:
            return '{"error": "not-authorized"}'

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("UPDATE highlows SET private=TRUE WHERE highlowid='{}';".format(self.high_low_id))

        self.isPrivate = True

        conn.commit()
        conn.close()

        return json.dumps( self.get_json(uid=uid, supports_html=supports_html) )

    def make_public(self, uid, supports_html=False):
        if uid != self.uid:
            return '{"error": "not-authorized"}'

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("UPDATE highlows SET private=FALSE WHERE highlowid='{}';".format(self.high_low_id))
        self.isPrivate = False


        conn.commit()
        conn.close()

        return json.dumps( self.get_json(uid=uid, supports_html=supports_html) )


    def update(self, uid, high=None, low=None, high_image=None, low_image=None, isPrivate=False, supports_html=False):
        
        self.update_high(uid, text=high, image=high_image, isPrivate=isPrivate)
        self.update_low(uid, text=low, image=low_image, isPrivate=isPrivate)

        return json.dumps(self.get_json(uid=self.uid, supports_html=supports_html))

    def update_high(self, uid, text=None, image=None, isPrivate=False, supports_html=False):
        if uid != self.uid:
            return '{"error": "not-authorized"}'
        self.isPrivate = isPrivate

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        if text is not None:
            text = pymysql.escape_string( self.sanitize_html(text) )
            self.high = text
            text = "'{}'".format(text)
        else:
            text = "NULL"

        filename = ""

        if image is not None:
            
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_high_images(image) )

            if 'error' in upload_result:
                conn.commit()
                conn.close()
                return json.dumps( upload_result )
        
            filename = "'{}'".format(upload_result["file"])
            self.high_image = upload_result["file"]
        else:
            filename = "NULL"

        #Update the data
        cursor.execute( "UPDATE highlows SET high={}, high_image={}, private={} WHERE highlowid='{}' AND uid='{}';".format(text, filename, "TRUE" if self.isPrivate else "FALSE",self.high_low_id, uid) )

        #Commit and close the connection
        conn.commit()
        conn.close()

        return json.dumps(self.get_json(uid=self.uid, supports_html=supports_html))

    def update_low(self, uid, text=None, image=None, isPrivate=False, supports_html=False):
        if uid != self.uid:
            return '{"error": "not-authorized"}'

        self.isPrivate = isPrivate

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        if text is not None:
            text = pymysql.escape_string( self.sanitize_html(text) )
            self.low = text
            text = "'{}'".format(text)
        else:
            text = "NULL"

        filename = ""

        if image is not None:
            
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_low_images(image) )

            if 'error' in upload_result:
                conn.commit()
                conn.close()
                return json.dumps( upload_result )
        
            filename = "'{}'".format(upload_result["file"])
            self.low_image = upload_result["file"]

        else:
            filename = "NULL"

        #Update the data
        cursor.execute( "UPDATE highlows SET low={}, low_image={}, private={} WHERE highlowid='{}' AND uid='{}';".format(text, filename, "TRUE" if self.isPrivate else "FALSE", self.high_low_id, uid) )

        #Commit and close the connection
        conn.commit()
        conn.close()

        return json.dumps(self.get_json(uid=self.uid, supports_html=supports_html))

    def delete(self):
        ## Delete the HighLow database entry ##
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Delete the entry
        cursor.execute("DELETE FROM highlows WHERE highlowid='" + self.high_low_id + "';")

        cursor.execute("DELETE FROM flags WHERE highlowid='{}';".format(self.high_low_id))

        cursor.execute("DELETE FROM likes WHERE highlowid='{}';".format(self.high_low_id))

        #Commit and close the connection
        conn.commit()
        conn.close()

    def update_total_likes(self):
        ## Count the number of likes in the database that belong to the current high/low ##
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute( "SELECT id FROM likes WHERE highlowid='{}';".format(self.high_low_id) )

        likes = cursor.fetchall()
        total_likes = len(likes)

        cursor.execute( "UPDATE highlows SET total_likes={} WHERE highlowid='{}';".format(total_likes, self.high_low_id) )

        conn.commit()
        conn.close()
    
    def like(self, uid):
        ## Add a new entry to the "Likes" table 
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Make sure this user hasn't "liked" before
        cursor.execute("SELECT * FROM likes WHERE highlowid='{}' AND uid='{}';".format(self.high_low_id, uid))

        if cursor.fetchone() is not None:
            conn.commit()
            conn.close()
            return { 'error': 'already-liked' }

        #Make sure the highlow does not belong to the user
        cursor.execute("SELECT uid FROM highlows WHERE highlowid='{}' AND uid='{}';".format(self.high_low_id, uid))

        if cursor.fetchone() is not None:
            conn.commit()
            conn.close()
            return { 'error': 'not-allowed' }

        #Create the entry
        cursor.execute( "INSERT INTO likes(highlowid, uid) VALUES('{}', '{}');".format(self.high_low_id, uid) )

        #Update the HighLow's total_likes
        cursor.execute( "UPDATE highlows SET total_likes = total_likes + 1 WHERE highlowid='{}';".format(self.high_low_id) )

        cursor.execute( "SELECT total_likes FROM highlows WHERE highlowid='{}';".format(self.high_low_id) )

        highlow = cursor.fetchone()

        cursor.execute( "SELECT firstname, lastname FROM users WHERE uid='{}';".format(uid))

        liker = cursor.fetchone()

        name = liker["firstname"] + " " + liker["lastname"]

        #Commit and close the connection
        conn.commit()
        conn.close()

        user = User(self.uid, self.host, self.username, self.password, self.database)

        if user.notify_new_like:
            notifs = Notifications(self.host, self.username, self.password, self.database)
            notifs.send_notification_to_user(name + " likes your post!", "You have received a like on one of your High/Lows!", self.uid, data={"highlowid": self.high_low_id})
        return { 'status': 'success', 'total_likes': highlow["total_likes"] }



    def unlike(self, uid):
        ## Remove the entry in the "Likes" table that corresponds to the current user and this high/low ##
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Update the High/Low's total likes
        cursor.execute( "SELECT * FROM likes WHERE highlowid='{}' AND uid='{}';".format(self.high_low_id, uid) )
        if cursor.fetchone() is not None:
            cursor.execute( "UPDATE highlows SET total_likes = total_likes - 1 WHERE highlowid='{}'".format(self.high_low_id) )

        #Delete the entry, if it exists
        cursor.execute( "DELETE FROM likes WHERE highlowid='{}' AND uid='{}';".format(self.high_low_id, uid) )

        cursor.execute( "SELECT total_likes FROM highlows WHERE highlowid='{}';".format(self.high_low_id) )

        highlow = cursor.fetchone()

        #Commit and close the connection
        conn.commit()
        conn.close()

        return json.dumps({ 'status': 'success', 'total_likes': highlow["total_likes"] })

    def comment(self, uid, message, request_id=None):
        #Collect the specified data and add to the database
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Check to see if this is a duplicate request. If it is, return the original response
        if request_id is not None:
            request_id = pymysql.escape_string( bleach.clean(request_id) )
            cursor.execute("SELECT * FROM onetime_requests WHERE request_id='{}';".format(request_id))

            duplicate = cursor.fetchone()

            if duplicate is not None:
                return json.loads(duplicate['response'])

        commentid = str( uuid.uuid1() )

        #Clean the message
        cleaned_message = pymysql.escape_string( bleach.clean(message) )

        if len(cleaned_message) == 0:
            return { "error": "no-comment" }

        cursor.execute( "INSERT INTO comments(commentid, highlowid, uid, message) VALUES('{}', '{}', '{}', '{}');".format(commentid, self.high_low_id, uid, cleaned_message) )

        cursor.execute("""
        SELECT DISTINCT
    comments.uid AS uid
FROM
    comments
JOIN users ON users.uid = comments.uid
WHERE comments.highlowid = '{}' AND users.notify_new_comment = TRUE AND comments.uid != '{}';
        """.format(self.high_low_id, uid))
        users = cursor.fetchall()

        other_user = User(uid, self.host, self.username, self.password, self.database)
        notifs = Notifications(self.host, self.username, self.password, self.database)

        if len(users) > 0:
            notifs.send_notification_to_users(other_user.firstname + " " + other_user.lastname + " commented on your discussion", bleach.clean(message), [user["uid"] for user in users], 4, data={"highlowid": self.high_low_id})
        
        notifs.send_notification_to_user(other_user.firstname + " " + other_user.lastname + " commented on your High/Low", bleach.clean(message), self.uid, data={"highlowid": self.high_low_id})
        
        conn.commit()
        conn.close()

        response = self.get_comments()

        #If a request ID was given, store it in the onetime requests table
        if request_id is not None:
            request_id = pymysql.escape_string( bleach.clean(request_id) )
            
            #Connect to MySQL
            conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO onetime_requests(request_id, response) VALUES('{}', '{}');".format(request_id, json.dumps(response)))
            conn.commit()
            conn.close()

        return response

    def update_comment(self, uid, commentid, message):
        #Find the comment and udpate the database
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cleaned_message = pymysql.escape_string( bleach.clean(message) )
        cleaned_commentid = pymysql.escape_string( bleach.clean(commentid) )
        
        cursor.execute( "UPDATE comments SET message='{}' WHERE commentid='{}' AND highlowid='{}' AND uid='{}';".format(cleaned_message, cleaned_commentid, self.high_low_id, uid) )

        conn.commit()
        conn.close()

    def delete_comment(self, uid, commentid):
        #Find the comment and udpate the database
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cleaned_commentid = pymysql.escape_string( bleach.clean(commentid) )

        cursor.execute( "DELETE FROM comments WHERE commentid='{}' AND uid='{}' AND highlowid='{}';".format(cleaned_commentid, uid, self.high_low_id) )

        conn.commit()
        conn.close()


    def get_comments(self):
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute( """
            SELECT
                commentid,
                comments.uid AS uid,
                message,
                _timestamp,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage
            FROM
                `comments`
                JOIN users ON users.uid = comments.uid
            WHERE comments.highlowid = '{}' ORDER BY _timestamp;
    """.format(self.high_low_id) )

        comments = cursor.fetchall()

        for i in range(len(comments)):
            comments[i]["_timestamp"] = comments[i]["_timestamp"].isoformat()

        conn.commit()
        conn.close()

        return comments


    def get(self, uid, column_name):

        column_name = pymysql.escape_string( bleach.clean(column_name) )

        if column_name in self.protected_columns:
            return '{ "error": "column_unavailable" }'

        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute( "SELECT {} FROM highlows WHERE highlowid='{}';".format(column_name, self.high_low_id) )

        result = cursor.fetchone()

        return json.dumps( { "result": result[column_name] } )

    def html_to_plain_text(self, html):
        soup = BeautifulSoup(html)
        return soup.get_text(separator='\n')

    def flag(self, uid, supports_html=False):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        _type = "highlow"

        #Check for duplicates
        cursor.execute( "SELECT * FROM flags WHERE flagger='{}' AND highlowid='{}' AND _type='highlow';".format(uid, self.high_low_id))

        if not cursor.fetchone():
            cursor.execute( "INSERT INTO flags(flagger, highlowid, uid, _type) VALUES('{}', '{}', '{}', '{}');".format(uid, self.high_low_id, self.uid, _type) )
            cursor.execute( "UPDATE users SET times_flagged = times_flagged + 1 WHERE uid='{}';".format(self.uid) )
        else:
            conn.commit()
            conn.close()
            return '{ "error": "already-flagged" }'

        conn.commit()
        conn.close()

        return json.dumps(self.get_json(uid=uid, supports_html=supports_html))

    def unflag(self, uid, supports_html=False):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute("SELECT id FROM flags WHERE highlowid='{}' AND flagger='{}';".format(self.high_low_id, uid))

        if cursor.fetchone() is not None:
            cursor.execute( """
            UPDATE users
            SET times_flagged = IF(times_flagged > 0, times_flagged - 1, 0)
            WHERE uid = '{}';""".format(self.uid) )
        
        cursor.execute( "DELETE FROM flags WHERE highlowid='{}' AND flagger='{}';".format(self.high_low_id, uid) )

        conn.commit()
        conn.close()

        return json.dumps(self.get_json(uid=uid, supports_html=supports_html))


class HighLowList:
    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database

    def get_highlows_for_user(self, uid, current_user, limit, page, sortby=None, supports_html=False):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        limit = int( pymysql.escape_string( bleach.clean( str(limit) ) ) )
        offset = int( pymysql.escape_string( bleach.clean( str(page) ) ) ) * limit

        cursor.execute("""
        
        SELECT
            highlows.uid AS uid,
            highlows.highlowid   AS highlowid,
            highlows.high        AS high,
            highlows.low         AS low,
            highlows.low_image   AS low_image,
            highlows.high_image  AS high_image,
            highlows._timestamp  AS _timestamp,
            highlows._date AS _date,
            highlows.total_likes AS total_likes,

            CASE
            WHEN flags.id IS NULL THEN 0
            ELSE 1
            END              AS flagged,

            CASE
            WHEN likes.id IS NULL THEN 0
            ELSE 1
            END              AS liked,
            highlows.private AS private

        FROM
            highlows
            LEFT OUTER JOIN flags ON flags.flagger = '{}' AND flags.highlowid = highlows.highlowid
            LEFT OUTER JOIN likes ON likes.uid = '{}' AND likes.highlowid = highlows.highlowid
        WHERE highlows.uid = '{}' AND (highlows.uid = '{}' OR highlows.private = FALSE)
        ORDER BY highlows._timestamp DESC LIMIT {} OFFSET {};
        
        """.format(current_user, current_user, uid, current_user, limit, offset))

        highlows = cursor.fetchall()

        if sortby is not None:

            options = {

                "latest": (None, False), 
                "oldest": (None, True),
                "most_likes": ("total_likes", True)

            }

            if options[sortby][0] is None:
                highlows = sorted(highlows, reverse=options[sortby][1])
            else:
                highlows = sorted(highlows, key=lambda a: a[ options[sortby][0] ], reverse=options[sortby][1])


        for highlow in highlows:
            highlow["_timestamp"] = highlow["_timestamp"].isoformat()

            cursor.execute( """
            SELECT
                commentid,
                comments.uid AS uid,
                message,
                _timestamp,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage
            FROM
                `comments`
                JOIN users ON users.uid = comments.uid
            WHERE comments.highlowid = '{}' ORDER BY _timestamp;
            """.format(highlow["highlowid"]) )

            highlow["flagged"] = highlow["flagged"] == 1
            highlow["liked"] = highlow["liked"] == 1
            highlow["private"] = highlow["private"] == 1
            highlow["comments"] = cursor.fetchall()

            if not supports_html:
                if highlow['high'] is not None:
                    highlow['high'] = self.html_to_plain_text(highlow['high'])
                if highlow['low'] is not None:
                    highlow['low'] = self.html_to_plain_text(highlow['low'])

            for i in highlow["comments"]:
                i["_timestamp"] = i["_timestamp"].isoformat()


        #Commit and close connection
        conn.commit()
        conn.close()

        return highlows


    def html_to_plain_text(self, html):
        soup = BeautifulSoup(html)
        return soup.get_text(separator='\n')

    def get_today_for_user(self, uid, supports_html=False):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        date = datetime.datetime.now()
        datestr = date.strftime("%Y-%m-%d")

        cursor.execute( "SELECT * FROM highlows WHERE uid='{}' AND _date = '{}';".format(uid, datestr) )

        highlow = cursor.fetchone()

        if highlow is None:
            conn.commit()
            conn.close()
            
            return {
                "high":"",
                "low":"",
                "uid": uid,
                "total_likes": 0,
                "high_image": "",
                "low_image": "",
                "date": "",
                "liked": "",
                "flagged": "",
                "comments": []
            }
        

        if not supports_html:
            if highlow['high'] is not None:
                highlow['high'] = self.html_to_plain_text(highlow['high'])
            if highlow['low'] is not None:
                highlow['low'] = self.html_to_plain_text(highlow['low'])

        cursor.execute( "SELECT * FROM likes WHERE uid='{}' AND _date='{}';".format(uid, datestr) )
        if cursor.fetchone() is not None:
            highlow["liked"] = True
        cursor.execute("SELECT * FROM flags WHERE uid='{}' AND _date='{}';".format(uid, datestr))
        if cursor.fetchone() is not None:
            highlow["flagged"] = True


        cursor.execute( """
            SELECT
                comments.highlowid AS highlowid,
                commentid,
                comments.uid AS uid,
                message,
                _timestamp,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage
            FROM
                `comments`
                JOIN users ON users.uid = comments.uid
            WHERE comments.highlowid = '{}' ORDER BY _timestamp;
        """.format(highlow["highlowid"]) )

        highlow["comments"] = cursor.fetchall()

        for i in highlow["comments"]:
            i["_timestamp"] = i["_timestamp"].isoformat()

        conn.commit()
        conn.close()

        highlow["_timestamp"] = highlow["_timestamp"].isoformat()

        return highlow

    def get_day_for_user(self, uid, date, viewer, supports_html=False):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        date = pymysql.escape_string( bleach.clean(date) )


        cursor.execute( "SELECT * FROM highlows WHERE uid='{}' AND _date = '{}';".format(uid, date) )

        highlow = cursor.fetchone()

        
        if highlow is None:
            conn.commit()
            conn.close()

            return {
                "high":"",
                "uid": uid,
                "low":"",
                "total_likes": 0,
                "high_image": "",
                "low_image": "",
                "date": "",
                "comments": []
            }

        if not supports_html:
            if highlow['high'] is not None:
                highlow['high'] = self.html_to_plain_text(highlow['high'])
            if highlow['low'] is not None:
                highlow['low'] = self.html_to_plain_text(highlow['low'])

        cursor.execute( "SELECT * FROM likes WHERE uid='{}' AND highlowid='{}'".format(viewer, highlow["highlowid"]) )
        if cursor.fetchone() is not None:
            highlow["liked"] = True
        cursor.execute("SELECT * FROM flags WHERE uid='{}' AND highlowid='{}'".format(viewer, highlow["highlowid"]))
        if cursor.fetchone() is not None:
            highlow["flagged"] = True


        cursor.execute( """
            SELECT
            comments.highlowid AS highlowid,
                commentid,
                comments.uid AS uid,
                message,
                _timestamp,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage
            FROM
                `comments`
                JOIN users ON users.uid = comments.uid
            WHERE comments.highlowid = '{}' ORDER BY _timestamp;
        """.format(highlow["highlowid"]) )

        highlow["comments"] = cursor.fetchall()

        for i in highlow["comments"]:
            i["_timestamp"] = i["_timestamp"].isoformat()

        conn.commit()
        conn.close()


        highlow["_timestamp"] = highlow["_timestamp"].isoformat()
        highlow["private"] = highlow["private"] == 1
        return highlow



class Comments:

    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database

    def delete_comment(self, uid, commentid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        commentid = pymysql.escape_string( bleach.clean(commentid) )

        cursor.execute("DELETE FROM comments WHERE uid='{}' AND commentid='{}';".format(uid, commentid))

        conn.commit()
        conn.close()

    def update_comment(self, uid, commentid, message):
        if message is None or message == "":
            return '{ "error": "no-message" }'


        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        commentid = pymysql.escape_string( bleach.clean(commentid) )

        message = pymysql.escape_string( bleach.clean(message) )

        cursor.execute("UPDATE comments SET message='{}' WHERE uid='{}' AND commentid='{}';".format(message, uid, commentid))

        conn.commit()
        conn.close()

        return '{"status": "success"}'
        