from google.cloud import storage
import bleach
import Helpers
import re
import pymysql


client = storage.Client()

bucket = client.lookup_bucket("highlowfiles")

#MySQL Config
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")

host = mysql_config["host"]
username = mysql_config["username"]
password = mysql_config["password"]
database = mysql_config["database"]


class FileStorage:

    def upload_image(self, file, uid):

        blob = bucket.blob( "user/{}/{}".format(uid, file.filename) )

        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )

        return '{ "file": "' + file.filename + '" }'

    def get_file(self, filename, uid):

        blob = bucket.blob( "user/{}/{}".format(uid, filename) )

        filestr = blob.download_as_string()

        return filestr

    def set_profileimage(self, image, uid):

        conn = pymysql.connect(host, username, password, database, cursorclass=pymysql.cursors.DictCursor)
        cursor = conn.cursor()

        cursor.execute( "SELECT FROM users WHERE uid='{}';".format(uid) )

        user = cursor.fetchone()

        if not user:
            return '{"error": "user-no-exist"}'

        #Make sure it's an image
        if re.search("(.+).(png|jpg|gif)", image.filename) == None:
            return '{"error": "Only PNG, JPG, and GIF formats are allowed"}'

        #Delete the old profile image
        oldimg = user["profileimage"]

        oldimg_blob = bucket.blob( "user/{}/{}".format(uid, oldimg) )

        oldimg_blob.delete()

        #Upload and set the new profile image
        newimg_blob = bucket.blob( "user/{}/{}".format(uid, image.filename) )

        newimg_blob.upload_from_string(image.read(), content_type=image.content_type)

        cursor.execute( "UPDATE users SET profileimage='{}' WHERE uid='{}';".format(image.filename, uid) )

        conn.commit()
        conn.close()

        return '{"file":"' + image.filename + '"}'