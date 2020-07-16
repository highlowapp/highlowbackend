import pymysql
import json
import bleach

class DB:
    def __init__(self, host, username, password, database):
        #Config used to create a connection
        self.host = host
        self.username = username
        self.password = password
        self.database = database

        #Connection and cursor objects
        self.conn = None
        self.cursor = None

        #Load SQL commands
        self.sql_cmds = {}

        with open('db/sql_cmds.json', 'r') as file:
            self.sql_cmds = json.loads( file.read() )


        #Automatic cleansing mode
        self.auto_cleanse = True

    def auto_cleanse(self):
        self.auto_cleanse = True

    def no_auto_cleanse(self):
        self.auto_cleanse = False

    def connect(self):
        #Create a connection to the DB
        self.conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        self.cursor = self.conn.cursor()
        

    def close(self):
        #Close a DB connection
        if self.conn is not None:
            self.conn.close()

    def cleanse_params(self, params):
        clean_params = []
        for param in params:
            if type(param) is str:
                param = pymysql.escape_string( bleach.clean(param) )
            clean_params.append(param)
        return clean_params
    
    def commit_and_close(self):
        #Commit and close a DB connection
        if self.conn is not None and self.conn.open:
            self.conn.commit()
            self.conn.close()

    def get_all(self, cmd, *params):
        #Get the SQL template
        sql = self.sql_cmds.get(cmd)

        #Raise error if it doesn't exist
        if sql is None:
            raise ValueError("SQL command '{}' not found".format(cmd))

        #Make sure there is an open connection
        if not self.conn or not self.conn.open:
            self.connect()

        #Check if automatic cleansing is on
        if self.auto_cleanse:
            params = self.cleanse_params(params)

        for param in params:
            if param is None:
                raise ValueError("Expected parameter but got 'None'")

        #Add parameters to SQL template
        sql_with_params = sql.format(*params)

        #Execute SQL command
        self.cursor.execute(sql_with_params)

        #Return all results
        return self.cursor.fetchall()
        
    def get_one(self, cmd, *params):
        #Get the SQL template
        sql = self.sql_cmds.get(cmd)

        #Raise error if it doesn't exist
        if sql is None:
            raise ValueError("SQL command '{}' not found".format(cmd))

        #Make sure there is an open connection
        if not self.conn or not self.conn.open:
            self.connect()

        #Check if automatic cleansing is on
        if self.auto_cleanse:
            params = self.cleanse_params(params)

        for param in params:
            if param is None:
                raise ValueError("Expected parameter but got 'None'")

        #Add parameters to SQL template
        sql_with_params = sql.format(*params)

        #Execute SQL command
        self.cursor.execute(sql_with_params)

        #Return one result
        return self.cursor.fetchone()

    def get(self, cmd, *params, **options):
        #Get the SQL template
        sql = self.sql_cmds.get(cmd)

        #Raise error if it doesn't exist
        if sql is None:
            raise ValueError("SQL command '{}' not found".format(cmd))

        #Make sure there is an open connection
        if not self.conn or not self.conn.open:
            self.connect()

        #Check if automatic cleansing is on
        if (options.get('auto_cleanse') is None and self.auto_cleanse) or options.get('auto_cleanse') is True:
            params = self.cleanse_params(params)

        for param in params:
            if param is None:
                raise ValueError("Expected parameter but got 'None'")

        #Add parameters to SQL template
        sql_with_params = sql.format(*params)

        #Execute SQL command
        self.cursor.execute(sql_with_params)

        #Return the result
        if options.get('single') is True:
            return self.cursor.fetchone()
        return self.cursor.fetchall()

    def execute(self, cmd, *params, **options):
        #Get the SQL template
        sql = self.sql_cmds.get(cmd)

        #Raise error if it doesn't exist
        if sql is None:
            raise ValueError("SQL command '{}' not found".format(cmd))

        for param in params:
            if param is None:
                raise ValueError("Expected parameter but got 'None'")

        #Make sure there is an open connection
        if not self.conn or not self.conn.open:
            self.connect()

        #Check if automatic cleansing is on
        if (options.get('auto_cleanse') is None and self.auto_cleanse) or options.get('auto_cleanse') is True:
            params = self.cleanse_params(params)

        #Add parameters to SQL template
        sql_with_params = sql.format(*params)

        #Execute SQL command
        self.cursor.execute(sql_with_params)