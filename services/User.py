import pymysql
import bleach
import json
import datetime
from services.FileStorage import FileStorage

class User:

    #Define initialization function
    def __init__(self, uid, host, username, password, database):
        self.uid = pymysql.escape_string( bleach.clean(uid) )
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        

        ## Get the user's data from MySQL ##

        #Connect to MySQL
        conn = pymysql.connect(host, username, password, database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Select the row with the user from the database
        cursor.execute("SELECT * FROM users WHERE uid='" + self.uid + "';")

        user = cursor.fetchone()

        #Commit and close the connection
        conn.commit()
        conn.close()

        #Make sure the user existed in the first place
        if user == None:
            raise ValueError("user-no-exist")

        #Otherwise, get all the data and store it
        self.firstname = user["firstname"]
        self.lastname = user["lastname"]
        self.userPassword = user["password"]
        self.email = user["email"]
        self.profileimage = user["profileimage"]
        self.bio = user["bio"]
        self.streak = user["streak"]
    
    ## Setters ##

    #Any column
    def set_column(self, column, value):

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        #Clean the values
        column = pymysql.escape_string( bleach.clean(column) )
        value = pymysql.escape_string( bleach.clean(value) )

        #Attempt to set the column
        cursor.execute("UPDATE users SET " + column + "='" + value + "' WHERE uid='" + self.uid + "';")

        #Commit and close the connection
        conn.commit()
        conn.close()

    def set_firstname(self, value):
        self.set_column("firstname", value)

    def set_lastname(self, value):
        self.set_column("lastname", value)

    def set_email(self, value):
        self.set_column("email", value)

    #NOTE: This function is different from the rest, because rather than using set_column, it utilizes the filestorage service
    def set_profileimage(self, image, uid):
        
        fileStorage = FileStorage()

        result = fileStorage.set_profileimage(image, uid)

        return result

    def set_default_profile_image(self):

        fileStorage = FileStorage()

        result = fileStorage.set_default_profile_image(self.uid)

        return result



    def set_password(self, value):
        print("WARNING: Setting the password can be dangerous!")
        self.set_column("password", value)

    def request_friend(self, uid):
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute("SELECT id FROM friends WHERE status!=0 AND ( (initiator='" + self.uid + "' AND acceptor='" + uid + "') OR (initiator='" + uid + "' AND acceptor='" + self.uid + "') );")

        duplicate = cursor.fetchone()

        if duplicate == None and self.uid != uid:
            cursor.execute("INSERT INTO friends(initiator, acceptor, status) VALUES('" + self.uid + "', '" + uid + "', 1)")

        conn.commit()
        conn.close()

        return { "status": "success" }

    def reject_friend(self, uid):
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute("UPDATE friends SET status=0 WHERE (initiator='" + self.uid + "' AND acceptor='" + uid + "') OR (initiator='" + uid + "' AND acceptor='" + self.uid + "');")

        conn.commit()
        conn.close()

        return { "status": "success" }

    def accept_friend(self, uid):
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')        
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute("UPDATE friends SET status=2 WHERE initiator='" + uid + "' AND acceptor='" + self.uid + "';")

        conn.commit()
        conn.close()

        return { "status": "success" }


    def list_friends(self):
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute( """
        
            SELECT
                frnds.friend_id AS uid,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage,
                users.streak AS streak,
                users.bio AS bio

            FROM

            (
                SELECT CASE
                    WHEN friends.initiator = '{}' THEN friends.acceptor
                    WHEN friends.acceptor = '{}' THEN friends.initiator
                END AS friend_id,
                friends.status AS status
                FROM friends
                WHERE (friends.initiator = '{}' OR friends.acceptor = '{}') AND friends.status = 2
            ) AS frnds

            JOIN users ON users.uid = frnds.friend_id;
        
        """.format(self.uid, self.uid, self.uid, self.uid) )


        friends = cursor.fetchall()

        conn.commit()
        conn.close()

        return { "friends": friends }

    
    def search_friends(self, search):
        #Clean the search
        search = pymysql.escape_string( bleach.clean(search) ).lower()


        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users;")

        users = cursor.fetchall() 

        cursor.execute("""
            SELECT 
                CASE
                    WHEN friends.initiator = '{}' THEN friends.acceptor
                    WHEN friends.acceptor = '{}' THEN friends.initiator
                END AS friend_id 
            FROM friends WHERE (friends.initiator = '{}' OR friends.acceptor = '{}') AND friends.status = 2;
            
        """.format(self.uid, self.uid, self.uid, self.uid) )

        friends = cursor.fetchall()

        conn.commit()
        conn.close()

        ranked_users = []

        for i in range( len(users) ):
            name = users[i]["firstname"] + " " + users[i]["lastname"]
            uid = users[i]["uid"]

            if uid == self.uid:
                continue

            shouldContinue = False

            for j in range( len(friends) ):
                if friends[j]["friend_id"] == uid:
                    shouldContinue = True
                    break
            
            if shouldContinue:
                continue

            rank = 0

            for j in range( len(name) ):

                if name[j] in search:
                    
                    if j < len(search):
                        if name[j] == search[j]:
                            rank += 2
                        else:
                            rank += 1
                    else:
                        rank += 1
            
            if rank > round( len(search) / 4):
                ranked_users.append( { "user": users[i], "rank": rank} )
            
        ranked_users = sorted(ranked_users, key = lambda i:i["rank"], reverse=True)


        return '{ "users": ' + json.dumps(ranked_users) + ' }'

    def list_pending_requests(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("""
        
            SELECT
                frnds.friend_id AS uid,
                users.firstname AS firstname,
                users.lastname AS lastname,
                users.profileimage AS profileimage,
                users.streak AS streak,
                users.bio AS bio

            FROM

            (
                SELECT CASE
                    WHEN friends.initiator = '{}' THEN friends.acceptor
                    WHEN friends.acceptor = '{}' THEN friends.initiator
                END AS friend_id,
                friends.status AS status
                FROM friends
                WHERE (friends.acceptor = '{}') AND friends.status = 1
            ) AS frnds

            JOIN users ON users.uid = frnds.friend_id;

        """.format(self.uid, self.uid, self.uid) ) 

        pending = cursor.fetchall()

        return '{ "requests": ' + json.dumps( pending ) + ' }' 


    def is_friend_with(self, uid):
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute( "SELECT status FROM friends WHERE (acceptor='{}' OR initiator='{}') AND (acceptor='{}' OR initiator='{}') AND status=2;".format(self.uid, self.uid, uid, uid) )

        row = cursor.fetchone()

        conn.commit()
        conn.close()


        if row == None:
            return '{"isFriend": false}'

        return '{"isFriend": true}'

    def flag(self, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        _type = "user"
         
        cursor.execute( "INSERT INTO flags(flagger, uid, _type) VALUES('{}', '{}', '{}');".format(uid, self.uid, _type) )

        conn.commit()
        conn.close()

        return '{"status": "success"}'

    def unflag(self, uid):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        uid = pymysql.escape_string( bleach.clean(uid) )

        cursor.execute( "DELETE FROM flags WHERE flagger='{}' AND uid='{}'".format(uid, self.uid) )

        conn.commit()
        conn.close()

        return '{"status": "success"}'


    def get_feed(self, limit, page):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        limit = int(pymysql.escape_string( bleach.clean( str(limit) ) ))
        offset = int( pymysql.escape_string( bleach.clean( str(page) ) ) ) * limit

        cursor.execute( """


            SELECT
                frnds.friend_id AS friend_id,
                highlows.highlowid   AS highlowid,
                highlows.high        AS high,
                highlows.low         AS low,
                highlows.low_image   AS low_image,
                highlows.high_image  AS high_image,
                highlows._timestamp  AS _timestamp,
                highlows._date AS _date,
                highlows.total_likes AS total_likes,
                users.firstname,
                users.lastname,
                users.profileimage,
                users.streak,
                users.bio,

                CASE
                WHEN flags.id IS NULL THEN 0
                ELSE 1
                END              AS flagged,

                CASE
                WHEN likes.id IS NULL THEN 0
                ELSE 1
                END              AS liked

            FROM
                (
                    SELECT
                    CASE
                    WHEN friends.initiator = '{}' THEN friends.acceptor
                    WHEN friends.acceptor = '{}' THEN friends.initiator
                    END
                    AS friend_id
                    FROM friends WHERE (friends.acceptor = '{}' OR friends.initiator = '{}') AND friends.status = 2

                ) AS frnds

                JOIN highlows ON highlows.uid = friend_id
                JOIN users ON users.uid = frnds.friend_id
                LEFT OUTER JOIN flags ON flags.flagger = '{}' AND flags.highlowid = highlows.highlowid
                LEFT OUTER JOIN likes ON likes.uid = '{}' AND likes.highlowid = highlows.highlowid

            ORDER BY highlows._timestamp DESC
            LIMIT {} OFFSET {};

            """.format(self.uid, self.uid, self.uid, self.uid, self.uid, self.uid, limit, offset) )

        raw_feed = cursor.fetchall()

        

        #Format the feed JSON (Normally I would say this wasn't a good idea, but in this case the size of the array is limited, so I think we'll be fine)
        feed = []
        print(raw_feed)
        for i in range(len(raw_feed)):

            #Get the comments
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
            """.format(raw_feed[i]["highlowid"]) )

            comments = cursor.fetchall()
            for j in comments:
                j["_timestamp"] = j["_timestamp"].isoformat()

            feed_item = {
                "user": {
                    "uid": raw_feed[i]["friend_id"],
                    "firstname": raw_feed[i]["firstname"],
                    "lastname": raw_feed[i]["lastname"],
                    "profileimage": raw_feed[i]["profileimage"],
                    "streak": raw_feed[i]["streak"],
                    "bio": raw_feed[i]["bio"]
                },
                "highlow": {
                    "highlowid": raw_feed[i]["highlowid"],
                    "high": raw_feed[i]["high"],
                    "low": raw_feed[i]["low"],
                    "high_image": raw_feed[i]["high_image"],
                    "low_image": raw_feed[i]["low_image"],
                    "_date": raw_feed[i]["_date"],
                    "_timestamp": raw_feed[i]["_timestamp"].isoformat(),
                    "total_likes": raw_feed[i]["total_likes"],
                    "uid": raw_feed[i]["friend_id"],
                    "comments": comments,
                    "liked": raw_feed[i]["liked"],
                    "flagged": raw_feed[i]["flagged"]
                }
            }

            feed.append(feed_item)

        conn.commit()
        conn.close()

        return '{ "feed": ' + json.dumps( feed ) + ' }'


    def calculate_streak(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT _date FROM highlows WHERE uid='{}' ORDER BY _date DESC LIMIT 1;".format(self.uid))

        most_recent_highlow = cursor.fetchone()

        most_recent_highlow_datetime = datetime.datetime.strptime(most_recent_highlow["_date"], "%Y-%m-%d") 

        diff = datetime.datetime.now() - most_recent_highlow_datetime

        value = self.streak
        if diff.days > 1:
            cursor.execute("UPDATE users SET streak=0 WHERE uid='{}';".format(self.uid))
            value = 0
        
        conn.commit()
        conn.close()

        return value

    def get_calendar(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute( "SELECT highlowid, _date FROM highlows WHERE uid='{}';".format(self.uid) )

        calendar = cursor.fetchall()

        conn.commit()
        conn.close()

        return { "calendar": calendar }
