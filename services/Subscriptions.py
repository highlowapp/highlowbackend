import pymysql
import bleach
import json
import datetime
import time
from pytz import timezone
import Helpers
import requests

subscription_config = Helpers.read_json_from_file('config/subscriptions_config.json')

class Subscriptions:
    def __init__(self, host, username, password, database):
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.secret = subscription_config['secret']
        self.overriden = subscription_config['overriden']

    def handleTransactionWithReceipt(receipt_data, uid, testing=False):
        json = {}

        #Get verification request
        if testing:
            json = self.validateReceiptSandbox(receipt_data)
        else:
            json = self.validateReceiptProd(receipt_data)

        #Get the status of the request
        status = json['status']

        if status == 0:
            latest_receipt = str(json['latest_receipt'])
            latest_receipt_info = json['latest_receipt_info']

            latest = latest_receipt_info[-1]

            originalTransactionId = latest['original_transaction_id']

            latest_expiry = latest_receipt_info['expires_date_ms']

            data = {
                'latestExpiryDate': latest_expiry,
                'latestReceiptData': latest_receipt
            }

            if latest_receipt_info['is_trial_period']:
                data['hasReceivedFreeTrial'] = True

            self.updateSubscriptionRecord(originalTransactionId, data)
            


        else if status == 21007:
            return self.handleTransactionWithReceipt(receipt_data, uid, testing=True)
        else:
            return {
                'error': 'invalid-receipt'
            }
        

    def validateReceiptSandbox(receipt_data):
        payload = {
            'receipt-data': receipt_data,
            'password': self.secret,
            'exclude-old-transactions': True
        }
        try:
            validation_req = requests.post('https://sandbox.itunes.apple.com/verifyReceipt', data=payload)

            return validation_req.json()
        except:
            return { 'status': 5 }


    def validateReceiptProd(receipt_data):
        payload = {
            'receipt-data': receipt_data,
            'password': self.secret,
            'exclude-old-transactions': True
        }

        try:
            validation_req = requests.post('https://buy.itunes.apple.com/verifyReceipt', data=payload)

            return validation_req.json()
        except: 
            return { 'status': 5 }

    def updateSubscriptionRecord(originalTransactionId, data):
        #Connect to the MySQL server
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        for key in data:
            data[key] = pymysql.escape_string( bleach.clean(data[key]) )

        cursor.execute("SELECT * FROM subscriptions WHERE originalTransactionId='{}';".format(originalTransactionId))

        existing_row = cursor.fetchone()

        if not existing_row:
            cursor.execute("INSERT INTO subscriptions(uid, originalTransactionId, latestExpiryDate, latestReceiptData, hasReceivedFreeTrial) VALUES('{}','{}','{}','{}',{});".format(data['uid'], data['originalTransactionId'], data['latestExpiryDate'], data['latestReceiptData'], data['hasReceivedFreeTrial']))
        else:
            latestExpiryDate = data.get('latestExpiryDate') or existing_row['latestExpiryDate']
            latestReceiptData = data.get('latestReceiptData') or existing_row['latestReceiptData']
            hasReceivedFreeTrial = data.get('hasReceivedFreeTrial') or existing_row['hasReceivedFreeTrial']

            cursor.execute("UPDATE subscriptions SET latestExpiryDate='{}' latestReceiptData='{}' hasReceivedFreeTrial={} WHERE originalTransactionId='{}'".format(latestExpiryDate, latestReceiptData, hasReceivedFreeTrial, originalTransactionId))

        conn.commit()
        conn.close()

    def isPayingUser(uid):
        #If we're overriden
        if self.overriden:
            return True

        #Connect to the MySQL server
        conn = pymysql.connect(self.host, self.username, self.password, self.database, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM subscriptions WHERE uid='{}';".format(uid))

        record = cursor.fetchone()

        if record is None:
            return False

        latestExpiryDate = record['latestExpiryDate']
        isHavingBillingIssues = record['isHavingBillingIssues']

        date1 = time.strptime(datetime.datetime.now().isoformat(), '%Y-%m-%dT%H:%M:%SZ')
        date2 = time.strptime(latestExpiryDate, '%Y-%m-%dT%H:%M:%SZ')
        date1 = time.mktime(date1)
        date2 = time.mktime(date2)

        dateDiff = date2 - date1

        if dateDiff < 0:
            if not isHavingBillingIssues:
                return (int(abs(dateDiff)) / 86400) > 4
            return False

        return True
