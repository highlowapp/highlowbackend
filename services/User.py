import pymysql
import bleach
import json
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

        if duplicate == None:
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
        search = pymysql.escape_string( bleach.clean(search) )

        #Separate into words (just using spaces currently)
        words = search.split(" ")
        
        #Create string
        word_list = "'" + "', '".join(words) + "'"


        #Connect to MySQL
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE LOWER(firstname) IN({}) OR LOWER(lastname) IN({});".format(word_list, word_list))

        results = cursor.fetchall()

        conn.commit()
        conn.close()

        return '{ "users": ' + json.dumps(results) + ' }'

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

        limit = pymysql.escape_string( bleach.clean( str(limit) ) )
        offset = int( pymysql.escape_string( bleach.clean( str(page) ) ) ) * limit

        cursor.execute( """


            SELECT 

            CASE 
                WHEN friends.initiator = '{}' THEN friends.acceptor
                WHEN friends.acceptor = '{}' THEN friends.initiator
            END AS friend_id,

            highlows.highlowid AS highlowid,
            highlows.high AS high,
            highlows.low AS low, 
            highlows.low_image AS low_image,
            highlows.high_image AS high_image, 
            highlows._timestamp AS _timestamp,
            highlows.total_likes AS total_likes,

            CASE
                WHEN flags.id IS NULL THEN 0
                ELSE 1
            END AS flagged,

            CASE 
                WHEN likes.id IS NULL THEN 0
                ELSE 1
            END AS liked
             
            FROM friends

            JOIN highlows ON highlows.uid = friend_id
            LEFT OUTER JOIN flags ON flags.flagger = '{}' AND flags.highlowid = highlows.highlowid
            LEFT OUTER JOIN likes ON likes.uid = '{}' AND likes.highlowid = highlows.highlowid

            WHERE (friends.initiator = '{}' OR friends.acceptor = '{}') AND friends.status = 2 ORDER BY highlows._timestamp DESC LIMIT {} OFFSET {};

            """.format(self.uid, self.uid, self.uid, self.uid, self.uid, self.uid, limit, offset) )

        feed = cursor.fetchall()

        conn.commit()
        conn.close()

        return '{ "feed": ' + json.dumps( feed ) + ' }'