import pymysql
import bleach
import uuid
import json
import datetime
from services.FileStorage import FileStorage
from services.Notifications import Notifications

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

        cursor.execute("SELECT interests.name FROM user_interests INNER JOIN interests ON interests.interest_id = user_interests.interest WHERE uid='" + self.uid + "';")

        interests = cursor.fetchall()

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
        self.times_flagged = user["times_flagged"]
        self.banned = user["banned"]
        self.notify_new_friend_req = user["notify_new_friend_req"]
        self.notify_new_friend_acc = user["notify_new_friend_acc"]
        self.notify_new_feed_item = user["notify_new_feed_item"]
        self.notify_new_like = user["notify_new_like"]
        self.notify_new_comment = user["notify_new_comment"]
        self.interests = [interest['name'] for interest in interests]
    
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

        if "status" in json.loads(result):
            #Connect to MySQL
            conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
            cursor = conn.cursor()

            cursor.execute("UPDATE users SET profileimage='{}' WHERE uid='{}';".format("user/" + uid + "/profile/profile.png", uid))
            
            conn.commit()
            conn.close()
            
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

        cursor.execute("SELECT id FROM friends WHERE status != 2 AND ( (initiator='" + self.uid + "' AND acceptor='" + uid + "') OR (initiator='" + uid + "' AND acceptor='" + self.uid + "') );")

        duplicate = cursor.fetchone()

        if duplicate is not None:
            cursor.execute("DELETE FROM friends WHERE status != 2 AND ( (initiator='" + self.uid + "' AND acceptor='" + uid + "') OR (initiator='" + uid + "' AND acceptor='" + self.uid + "') );")

        if self.uid != uid:
            cursor.execute("INSERT INTO friends(initiator, acceptor, status) VALUES('" + self.uid + "', '" + uid + "', 1)")


        conn.commit()
        conn.close()

        other_user = User(uid, self.host, self.username, self.password, self.database)
        
        if other_user.notify_new_friend_req:
            notifs = Notifications(self.host, self.username, self.password, self.database)
            notifs.send_notification_to_user("New Friend Request", self.firstname + " " + self.lastname + " has requested your friendship", uid, data={"uid": uid})
        
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
        


        try:
            other_user = User(uid, self.host, self.username, self.password, self.database)
            
            if other_user.notify_new_friend_acc:
                notifs = Notifications(self.host, self.username, self.password, self.database)
                notifs.send_notification_to_user("Friendship Accepted!", self.firstname + " " + self.lastname + " has accepted your friendship!", uid, data={"uid": uid})
        except:
            pass

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

        for friend in friends:
            cursor.execute("SELECT interests.name AS name FROM user_interests INNER JOIN interests ON interests.interest_id = user_interests.interest WHERE uid='" + friend['uid'] + "';")
            interests = [interest['name'] for interest in cursor.fetchall()]
            friend['interests'] = interests

        conn.commit()
        conn.close()

        return { "friends": friends }

    def get_friend_uids(self):
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute( """
        
            SELECT
                frnds.friend_id AS uid
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

        uids = []

        for friend in friends:
            uids.append(friend["uid"])

        return uids


    
    def search_friends(self, search):
        #Clean the search
        search = pymysql.escape_string( bleach.clean(search) ).lower()


        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT uid, firstname, lastname, email, profileimage, streak, bio FROM users WHERE banned=FALSE;")

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


    def get_feed(self, limit, page, supports_html=False):
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
                END
                 AS flagged,

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

            WHERE (highlows.uid = '{}' OR highlows.private = FALSE)
            ORDER BY highlows._timestamp DESC
            LIMIT {} OFFSET {};

            """.format(self.uid, self.uid, self.uid, self.uid, self.uid, self.uid, self.uid, limit, offset) )

        raw_feed = cursor.fetchall()

        

        #Format the feed JSON (Normally I would say this wasn't a good idea, but in this case the size of the array is limited, so I think we'll be fine)
        feed = []

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

            cursor.execute("SELECT interests.name AS name FROM user_interests INNER JOIN interests ON interests.interest_id = user_interests.interest WHERE uid='" + raw_feed[i]['friend_id'] + "';")

            interests = [interest['name'] for interest in cursor.fetchall()]

            feed_item = {
                "user": {
                    "uid": raw_feed[i]["friend_id"],
                    "firstname": raw_feed[i]["firstname"],
                    "lastname": raw_feed[i]["lastname"],
                    "profileimage": raw_feed[i]["profileimage"],
                    "streak": raw_feed[i]["streak"],
                    "bio": raw_feed[i]["bio"],
                    "interests": interests
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
                    "liked": (raw_feed[i]["liked"] == 1),
                    "flagged": (raw_feed[i]["flagged"] == 1)
                }
            }

            if not supports_html:
                if feed_item['highlow']['high'] is not None:
                    feed_item['highlow']['high'] = self.html_to_plain_text(feed_item['highlow']['high'])
                if feed_item['highlow']['low'] is not None:
                    feed_item['highlow']['low'] = self.html_to_plain_text(feed_item['highlow']['low'])

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

        if most_recent_highlow is None:
            return 0

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

    def ban(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET banned=TRUE WHERE uid='{}'".format(self.uid))

        conn.commit()
        conn.close()

        return { "status": "success" }

    def unban(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET banned=FALSE WHERE uid='{}'".format(self.uid))

        conn.commit()
        conn.close()

        return { "status": "success" }

    def get_notif_settings(self):
        return {
            "notify_new_friend_req": self.notify_new_friend_req == 1,
            "notify_new_friend_acc": self.notify_new_friend_acc == 1,
            "notify_new_feed_item": self.notify_new_feed_item == 1,
            "notify_new_like": self.notify_new_like == 1,
            "notify_new_comment": self.notify_new_comment == 1
        }

    def set_notif_setting(self, setting, value):
        if setting not in ['notify_new_friend_req', 'notify_new_friend_acc', 'notify_new_feed_item', 'notify_new_like', 'notify_new_comment']:
            raise ValueError("Invalid setting")
        
        if value not in (True, False):
            raise ValueError("Invalid value")

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()
        
        if value:
            cursor.execute("UPDATE users SET {}=TRUE WHERE uid='{}';".format(setting, self.uid))
        else:
            cursor.execute("UPDATE users SET {}=FALSE WHERE uid='{}';".format(setting, self.uid))
        
        conn.commit()
        conn.close()

        return { "status": "success" }



    def add_interests(self, interests):
        if interests is None:
            return { "error": "no-interests-provided" }


        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()
        
        for interest in interests:
            interest = pymysql.escape_string( bleach.clean(interest) )

            #Check for existing interest
            cursor.execute("SELECT * FROM user_interests WHERE uid='{}' AND interest='{}';".format(self.uid, interest))

            dups = cursor.fetchone()

            if dups is None:
                cursor.execute("INSERT INTO user_interests(uid, interest) VALUES('{}','{}');".format(self.uid, interest))

        conn.commit()
        conn.close()

        return { "status": "success" }

    def remove_interests(self, interests):
        if interests is None:
            return { "error": "no-interests-provided" }

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()
        
        for interest in interests:
            interest = pymysql.escape_string( bleach.clean(interest) )
            cursor.execute("DELETE FROM user_interests WHERE uid='{}' AND interest='{}';".format(self.uid, interest))

        conn.commit()
        conn.close()

        return { "status": "success" }

    def create_interest(self, name):
        name = pymysql.escape_string( bleach.clean(name) ).lower()
        if name is None or len(name) == 0: 
            return { "error": "no-name-provided" }

        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        interest_id = uuid.uuid1()

        #Check for duplicates
        cursor.execute("SELECT * FROM interests WHERE name='{}';".format(name))

        duplicate_entries = cursor.fetchone()

        if duplicate_entries is not None:
            interest_id = duplicate_entries["interest_id"]
        else:
            cursor.execute("INSERT INTO interests(name, interest_id) VALUES('{}', '{}');".format(name, interest_id))
        
        #Check for existing interest
        cursor.execute("SELECT * FROM user_interests WHERE uid='{}' AND interest='{}';".format(self.uid, interest_id))

        dups = cursor.fetchone()

        if dups is None:
            cursor.execute("INSERT INTO user_interests(uid, interest) VALUES('{}', '{}');".format(self.uid, interest_id))

        conn.commit()
        conn.close()

        return { "status": "success", "interest_id": str(interest_id) } 

    def get_interests(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT interests.name, interests.interest_id FROM user_interests INNER JOIN interests ON interests.interest_id = user_interests.interest WHERE uid='" + self.uid + "';")

        interests = cursor.fetchall()

        conn.commit()
        conn.close()

        return { "interests": interests }

    def get_all_interests(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT name, interest_id FROM interests;")

        interests = cursor.fetchall()

        conn.commit()
        conn.close()

        return { "interests": interests }

    def get_mutual_interests(self):
        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("""
        
        SELECT DISTINCT
            users.uid uid,
            users.firstname firstname,
            users.lastname lastname,
            users.profileimage profileimage,
            users.streak streak,
            users.bio bio
        FROM
        (SELECT * FROM user_interests WHERE uid='{}') my_interests

        JOIN user_interests others_interests ON others_interests.interest = my_interests.interest AND others_interests.uid != '{}'
        JOIN users ON users.uid = others_interests.uid;
        
        """.format(self.uid, self.uid))

        common_interest_users = cursor.fetchall()

        cursor.execute("""
        
        SELECT
            frnds.friend_id AS uid
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

        """.format(self.uid, self.uid, self.uid, self.uid))

        friends = cursor.fetchall()

        conn.commit()
        conn.close()

        friends_set = set()

        for friend in friends:
            friends_set.add(friend["uid"])

        users = filter(lambda x: (x["uid"] not in friends_set), common_interest_users)

        return { 
            "users": list(users)
        }