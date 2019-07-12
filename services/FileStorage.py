from google.cloud import storage
import bleach
import Helpers
import re
import pymysql
import uuid
import bleach
from io import BytesIO
from PIL import Image

HIGHLOW_IMAGE_SIZE = (800, 600)
PROFILE_IMAGE_SIZES = [(128, 128), (64, 64), (32, 32)]

SUPPORTED_MIMETYPES = ["image/png", "image/jpeg", "image/gif"]
SUPPORTED_FILE_EXTENSIONS = ["png", "jpeg", "jpg", "gif"]

#MySQL Config
mysql_config = Helpers.read_json_from_file("config/mysql_config.json")

host = mysql_config["host"]
username = mysql_config["username"]
password = mysql_config["password"]
database = mysql_config["database"]


class FileStorage:

    def upload_image(self, file, uid):
        client = storage.Client()

        bucket = client.lookup_bucket("highlowfiles")

        blob = bucket.blob( "user/{}/{}".format(uid, file.filename) )

        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )

        return '{ "file": "' + file.filename + '" }'

    def get_file(self, filename, uid):
        client = storage.Client()

        bucket = client.lookup_bucket("highlowfiles")

        blob = bucket.blob( "user/{}/{}".format(uid, filename) )

        filestr = blob.download_as_string()

        return filestr

    #TODO: Check that they are actually images
    def upload_to_high_images(self, file):

        client = storage.Client()

        bucket = client.lookup_bucket("highlowfiles")

        file_content = BytesIO( file.read() )

        #Make sure it's an image
        file_extension = file.filename.split(".")[-1]

        if file_extension.lower() not in SUPPORTED_FILE_EXTENSIONS:
            return '{"error": "Only PNG, JPG, and GIF formats are allowed", "invalid_extension": "' + file_extension + '"}'

        #Check MIME type
        if file.mimetype not in SUPPORTED_MIMETYPES:
            return '{"error": "Unsupported MIMETYPE. Supported MIMETYPES are ' + ", ".join(SUPPORTED_MIMETYPES) + '"}'



        #Resize the image
        img = Image.open(file_content)
        img.resize(HIGHLOW_IMAGE_SIZE)
        resized_img = BytesIO()
        img.save(resized_img, format="PNG")



        filename = str( uuid.uuid1() ) + ".png"

        blob = bucket.blob( "highs/{}".format(filename) )

        blob.upload_from_string(
            resized_img.getvalue(),
            content_type=file.content_type
        )

        return '{ "file": "' + filename + '" }'






    def upload_to_low_images(self, file):

        client = storage.Client()

        bucket = client.lookup_bucket("highlowfiles")

        file_content = BytesIO( file.read() )

        #Make sure it's an image
        file_extension = file.filename.split(".")[-1]
        if file_extension.lower() not in SUPPORTED_FILE_EXTENSIONS:
            return '{"error": "Only PNG, JPG, and GIF formats are allowed"}'


        #Check MIME type
        if file.mimetype not in SUPPORTED_MIMETYPES:
            return '{"error": "Unsupported MIMETYPE. Supported MIMETYPES are ' + ", ".join(SUPPORTED_MIMETYPES) + '"}'



        #Resize the image
        img = Image.open(file_content)
        img.resize(HIGHLOW_IMAGE_SIZE)
        resized_img = BytesIO()
        img.save(resized_img, format="PNG")


        filename = str( uuid.uuid1() ) + ".png"

        blob = bucket.blob( "lows/{}".format(filename) )

        blob.upload_from_string(
            resized_img.getvalue(),
            content_type=file.content_type
        )

        return '{ "file": "' + filename + '" }'

    def set_profileimage(self, image, uid):

        client = storage.Client()

        bucket = client.lookup_bucket("highlowfiles")


        file_content = BytesIO( image.read() )


        #Make sure it's an image
        file_extension = image.filename.split(".")[-1]
        if file_extension.lower() not in SUPPORTED_FILE_EXTENSIONS:
            return '{"error": "Only PNG, JPG, and GIF formats are allowed"}'


        #Check MIME type
        if image.mimetype.lower() not in SUPPORTED_MIMETYPES:
            return '{"error": "Unsupported MIMETYPE. Supported MIMETYPES are ' + ", ".join(SUPPORTED_MIMETYPES) + '"}'



        img = Image.open( file_content )
        img.resize(PROFILE_IMAGE_SIZES[0])
        resized_img = BytesIO()
        img.save(resized_img, format="PNG")

        blob = bucket.blob( "user/{}/profile/profile.png".format(uid, str( uuid.uuid1() ) ) )

        blob.upload_from_string(
            resized_img.getvalue(),
            content_type=image.content_type
        )

        #If you want to copy the image into multiple sizes, use the below code

        """

        for size in PROFILE_IMAGE_SIZES:
            img = Image.open( file_content )
            img.resize(size)
            resized_img = BytesIO()
            img.save(resized_img, format="PNG")

            blob = bucket.blob( "user/{}/profile/{}x{}.png".format(uid, size[0], size[1]) )

            blob.upload_from_string(
                resized_img.getvalue(),
                content_type=image.content_type
            )
        """
        

        return '{"status":"success"}'




    def set_default_profile_image(self, uid):

        client = storage.Client()

        bucket = client.lookup_bucket("highlowfiles")

        source_blob = bucket.blob("default_profile_image.png")

        new_blob = bucket.copy_blob(source_blob, bucket, "user/{}/profile/profile.png")

        return '{"status": "success"}'