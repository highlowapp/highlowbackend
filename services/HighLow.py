import pymysql
import requests
import uuid
import time
import datetime
import bleach
import json
from services.FileStorage import FileStorage

class HighLow:

    def __init__(self, host, username, password, database, high_low_id=None):
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.high_low_id = ""

        if high_low_id != None:
            self.high_low_id = pymysql.escape_string( bleach.clean(high_low_id) )

            conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
            cursor = conn.cursor()
            cursor.execute( "SELECT * FROM highlows WHERE highlowid='{}';".format(self.high_low_id) )
            result = cursor.fetchone()
            conn.commit()
            conn.close()

            if not result:
                raise ValueError("highlow-no-exist")

            self.high = result["high"]
            self.low = result["low"]
            self.high_image = result["high_image"]
            self.low_image = result["low_image"]
            self.timestamp = result["_timestamp"]
            self.total_likes = result["total_likes"]

        self.high = ""
        self.low = ""
        self.high_image = ""
        self.low_image = ""
        self.timestamp = None
        self.total_likes = 0
        self.protected_columns = []

    def create(self, uid, high=None, low=None, high_image=None, low_image=None):
        ## Create a new High/Low entry in the database ##

        #Create a High/Low ID
        self.high_low_id = str( uuid.uuid1() )

        if high != None:
            self.high = pymysql.escape_string( bleach.clean(high) )
            self.high = "'{}'".format(self.high)
        else:
            self.high = "NULL"

        if low != None:
            self.low = pymysql.escape_string( bleach.clean(low) )
            self.low = "'{}'".format(self.low)
        else:
            self.low = "NULL"

        if high_image != None:
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_high_images(high_image) )

            if 'error' in upload_result:
                return json.dumps( upload_result )
        
            self.high_image = "'{}'".format(upload_result["file"])
        else:
            self.high_image = "NULL"

        if low_image != None:
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_high_images(low_image) )

            if 'error' in upload_result:
                return json.dumps( upload_result )
        
            self.low_image = "'{}'".format(upload_result["file"])
        else:
            self.low_image = "NULL"

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Now, insert the data
        cursor.execute("INSERT INTO highlows(highlowid, uid, high, low, high_image, low_image, total_likes) VALUES('{}', '{}', {}, {}, {}, {}, 0);".format(self.high_low_id, uid, self.high, self.low, self.high_image, self.low_image) )

        #Commit and close the connection
        conn.commit()
        conn.close()
        
        #Return the HighLow ID
        return '{ "highlowid":"' + self.high_low_id + '" }'


    def get_json(self):
        json_object = {
            "high": self.high,
            "low": self.low, 
            "high_image": self.high_image,
            "low_image": self.low_image,
            "total_likes": self.total_likes,
            "highlowid": self.high_low_id,
            "timestamp": self._timestamp
        }

        return json_object


    def update(self, uid, high=None, low=None, high_image=None, low_image=None):
        
        self.update_high(uid, text=high, image=high_image)
        self.update_low(uid, text=low, image=low_image)

    def update_high(self, uid, text=None, image=None):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()



        if text != None:
            text = pymysql.escape_string( bleach.clean(text) )
            text = "'{}'".format(text)
        else:
            text = "NULL"

        filename = ""

        if image != None:
            
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_high_images(image) )

            if 'error' in upload_result:
                return json.dumps( upload_result )
        
            filename = "'{}'".format(upload_result["file"])

        else:
            filename = "NULL"

        self.high = text
        self.high_image = image

        #Update the data
        cursor.execute( "UPDATE highlows SET high={}, high_image={} WHERE highlowid='{}' AND uid='{}';".format(text, filename, self.high_low_id, uid) )

        #Commit and close the connection
        conn.commit()
        conn.close()

        return '{"status": "success"}'

    def update_low(self, uid, text=None, image=None):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        if text != None:
            text = pymysql.escape_string( bleach.clean(text) )
            text = "'{}'".format(text)
        else:
            text = "NULL"

        filename = ""

        if image != None:
            
            fileStorage = FileStorage()

            upload_result = json.loads( fileStorage.upload_to_low_images(image) )

            if 'error' in upload_result:
                return json.dumps( upload_result )
        
            filename = "'{}'".format(upload_result["file"])

        else:
            filename = "NULL"

        self.low = text
        self.low_image = image

        #Update the data
        cursor.execute( "UPDATE highlows SET low={}, low_image={} WHERE highlowid='{}' AND uid='{}';".format(text, filename, self.high_low_id, uid) )

        #Commit and close the connection
        conn.commit()
        conn.close()

        return '{"status": "success"}'

    def delete(self):
        ## Delete the HighLow database entry ##
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Delete the entry
        cursor.execute("DELETE FROM highlows WHERE highlowid='" + self.high_low_id + "';")

        #Commit and close the connection
        conn.commit()
        conn.close()

    def update_total_likes(self):
        ## Count the number of likes in the database that belong to the current high/low ##
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute( "SELECT id FROM likes WHERE highlowid='{}'".format(self.high_low_id) )

        likes = cursor.fetchall()
        total_likes = len(likes)

        cursor.execute( "UPDATE highlows SET total_likes={} WHERE highlowid='{}'".format(total_likes, self.high_low_id) )

        conn.commit()
        conn.close()
    
    def like(self, uid):
        ## Add a new entry to the "Likes" table 
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Make sure this user hasn't "liked" before
        cursor.execute("SELECT * FROM likes WHERE highlowid='{}' AND uid='{}';".format(self.high_low_id, uid))

        if cursor.fetchone() != None:
            conn.commit()
            conn.close()
            return { 'error': 'already-liked' }

        #Make sure the highlow does not belong to the user
        cursor.execute("SELECT uid FROM highlows WHERE highlowid='{}'".format(self.high_low_id))

        if cursor.fetchone() != None:
            conn.commit()
            conn.close()
            return { 'error': 'not-allowed' }

        #Create the entry
        cursor.execute( "INSERT INTO likes(highlowid, uid) VALUES('{}', '{}');".format(self.high_low_id, uid) )

        #Commit and close the connection
        conn.commit()
        conn.close()

        return { 'status': 'success'}



    def unlike(self, uid):
        ## Remove the entry in the "Likes" table that corresponds to the current user and this high/low ##
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Delete the entry, if it exists
        cursor.execute( "DELETE FROM likes WHERE highlowid='{}' AND uid='{}';".format(self.high_low_id, uid) )

        #Commit and close the connection
        conn.commit()
        conn.close()

    def comment(self, uid, message):
        #Collect the specified data and add to the database
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        commentid = str( uuid.uuid1() )

        #Clean the message
        cleaned_message = pymysql.escape_string( bleach.clean(message) )

        cursor.execute( "INSERT INTO comments(commentid, highlowid, uid, message) VALUES('{}', '{}', '{}', '{}');".format(commentid, self.high_low_id, uid, cleaned_message) )

        conn.commit()
        conn.close()

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
                comments.uid,
                message,
                _timestamp,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage
            FROM
                `comments`
                JOIN users ON users.uid = comments.uid
            WHERE comments.highlowid = '{}';
    """.format(self.high_low_id) )

        comments = cursor.fetchall()

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

    def flag(self, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        _type = "highlow"
         
        cursor.execute( "INSERT INTO flags(flagger, highlowid, _type) VALUES('{}', '{}', '{}');".format(uid, self.high_low_id, _type) )

        conn.commit()
        conn.close()

        return '{"status": "success"}'

    def unflag(self, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )
         
        cursor.execute( "DELETE FROM flags WHERE highlowid='{}' AND flagger='{}';".format(self.high_low_id, uid) )

        conn.commit()
        conn.close()

        return '{"status": "success"}'


class HighLowList:
    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database

    def get_highlows_for_user(self, uid, sortby=None, limit=None):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        if limit != None:
            limit = "LIMIT " + pymysql.escape_string( bleach.clean(limit) )
        else:
            limit = ""

        cursor.execute("SELECT * FROM highlows WHERE uid='{}' {} ORDER BY _timestamp DESC;".format(uid, limit))

        highlows = cursor.fetchall()

        if sortby != None:

            options = {

                "latest": (None, False), 
                "oldest": (None, True),
                "most_likes": ("total_likes", True)

            }

            if options[sortby][0] == None:
                highlows = sorted(highlows, reverse=options[sortby][1])
            else:
                highlows = sorted(highlows, key=lambda a: a[ options[sortby][0] ], reverse=options[sortby][1])

        #Commit and close connection
        conn.commit()
        conn.close()

        return highlows

    def get_today_for_user(self, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute( "SELECT * FROM highlows WHERE uid='{}' AND DATE(_timestamp) = CURDATE();".format(uid) )

        highlow = cursor.fetchone()

        conn.commit()
        conn.close()

        if highlow == None:
            return {
                "high":"",
                "low":"",
                "total_likes": 0,
                "high_image": "",
                "low_image": ""
            }

        highlow["_timestamp"] = datetime.datetime.timestamp(highlow["_timestamp"])

        return highlow
        