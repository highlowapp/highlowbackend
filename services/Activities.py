import Helpers
import db
import uuid
import json
import pymysql
import bleach
from services.Subscriptions import Subscriptions
from services.FileStorage import FileStorage
from datetime import datetime
from datetime import timedelta

DATE_FORMAT = "%Y-%m-%d"

class Activities:
    def __init__(self, host, username, password, database):
        self.db = db.DB(host, username, password, database)

        self.activity_types = Helpers.read_json_from_file('activity_types.json')

        self.subscriptions = Subscriptions(host, username, password, database)
        self.file_storage = FileStorage()

    def has_flagged(self, uid, activity_id):
        record = self.db.get_one('has_flagged', uid, activity_id)
        if record is not None:
            return True
        return False

    def data_fits_free_plan(self, _type, data):
        json_data = json.loads(data)
        print(_type)
        print(json_data)
        if _type in ('diary', 'highlow'):
            blocks = json_data['blocks']
            if len(blocks) > 10:
                return False

            num_images = 0
            for block in blocks:
                if block['type'] is 'img':
                    num_images += 1
            
            if num_images > 2:
                return False
        
        return True

    def data_allowed_for_subscription(self, uid, _type, data):
        uid = pymysql.escape_string( bleach.clean(uid) )
        is_subscriber = self.subscriptions.isPayingUser(uid)
        if is_subscriber:
            return True
        
        return self.data_fits_free_plan(_type, data)

    def close_and_return(self, value):
        self.db.commit_and_close()
        return value

    def verify_activity_data(self, _type, data):
        if type(_type) is not str:
            return False
        
        try:
            json_data = json.loads(data)
            
            for key in self.activity_types[_type]:
                if key not in json_data:
                    return False

        except: 
            return False

        return True

    def share_categories(self, uid, is_friend):
        if is_friend:
            return ('all', 'friends', uid)
        return ('all', uid)

    def activity_from_record(self, record):
        record['data'] = json.loads(record['data'])
        record['timestamp'] = record['timestamp'].isoformat()
        return record

    def has_access(self, uid, activity_id):
        record = self.db.get_one('get_activity', activity_id)

        if record is None:
            self.db.commit_and_close()
            return None, None
        
        activity = self.activity_from_record(record)

        records = self.db.get_all('get_activity_comments', activity_id)

        for record in records:
            record['timestamp'] = record['timestamp'].isoformat()
        
        activity['comments'] = records

        owner = activity['uid']

        sharing = self.db.get_all('get_sharing_policy', activity_id)
        activity['flagged'] = self.has_flagged(uid, activity_id)

        if owner is uid:
            sharing_policy = []
            for policy in sharing:
                if policy['shared_with'] in ('all', 'none', 'friends'):
                    sharing_policy = [ policy['shared_with'] ]
                else:
                    sharing_policy.append(policy['shared_with'])

            self.db.commit_and_close()

            activity['sharing_policy'] = sharing_policy

            return True, activity

        is_friend = self.db.get_one('is_friend', uid, owner) is not None

        

        for share in sharing:
            if share['shared_with'] in self.share_categories(uid, is_friend):
                self.db.commit_and_close()
                return True, activity

        self.db.commit_and_close()
        return False, None

    def add(self, uid, _type, data, date):
        #Create activity ID
        activity_id = str( uuid.uuid1() )

        #Check data is valid
        if self.verify_activity_data(_type, data):
            if not self.data_allowed_for_subscription(uid, _type, data):
                return self.close_and_return({ 'error': 'requires-subscription' })
            self.db.execute('add_activity', activity_id, uid, json.loads(data)['title'], _type, data, date)
            record = self.db.get_one('get_user_activity', uid, activity_id)
            activity = self.activity_from_record(record)

            comments = self.db.get_all('get_activity_comments', activity['activity_id'])
            for comment in comments:
                comment['timestamp'] = comment['timestamp'].isoformat()

            activity['comments'] = comments

            activity['flagged'] = self.has_flagged(uid, activity_id)
            return self.close_and_return(activity)
        return self.close_and_return({ 'error': 'invalid-data' })

    def get_by_id(self, uid, activity_id):
        has_access, activity = self.has_access(uid, activity_id)
        
        if activity is None:
            return self.close_and_return({ 'error': ('access-denied' if has_access is False else 'does-not-exist')})

        activity['flagged'] = self.has_flagged(uid, activity_id)

        return self.close_and_return(activity)

    def is_friend(self, uid, other):
        record = self.db.get_one('is_friend', uid, other)
        if record is not None:
            return self.close_and_return(True)
        return self.close_and_return(False)

    def get_diary_entries(self, uid, page=0):
        page = 0 if page is None else page
        if type(page) is not int:
            return self.close_and_return({ 'error': 'page-must-be-int' })
        
        records = None

        records = self.db.get_all('get_user_diary_entries', uid, page * 10)
        
        activities = []

        for record in records:
            activity = self.activity_from_record(record)

            comments = self.db.get_all('get_activity_comments', activity['activity_id'])
            for comment in comments:
                comment['timestamp'] = comment['timestamp'].isoformat()

            activity['comments'] = comments

            activities.append(activity)

        return self.close_and_return({
            'activities': activities
        })


    def get_for_user(self, uid, viewer, page=0):
        page = 0 if page is None else page
        if type(page) is not int:
            return self.close_and_return({ 'error': 'page-must-be-int' })

        records = None

        if viewer is uid:
            records = self.db.get_all('get_user_activities', uid, page * 10)
        else:
            if self.is_friend(viewer, uid):
                records = self.db.get_all('view_friend_activities', uid, viewer)
            else:
                records = self.db.get_all('view_stranger_activities', viewer)

        activities = []

        for record in records:
            activity = self.activity_from_record(record)

            comments = self.db.get_all('get_activity_comments', activity['activity_id'])
            for comment in comments:
                comment['timestamp'] = comment['timestamp'].isoformat()

            activity['comments'] = comments
            activity['flagged'] = self.has_flagged(uid, activity['activity_id'])

            activities.append(activity)


        return self.close_and_return({
            'activities': activities
        })

    def update(self, uid, activity_id, data):
        record = self.db.get_one('get_user_activity', uid, activity_id)
        if record is None:
            return self.close_and_return({ 'error': 'access-denied' })
        
        activity = self.activity_from_record(record)

        _type = activity['type']
        
        if not self.verify_activity_data(_type, data):
            return self.close_and_return({ 'error': 'invalid-data' })
        
        new_data = {**activity['data'], **json.loads(data)}

        self.db.execute('update_activity', json.dumps(new_data), uid, activity_id)
        
        activity['data'] = new_data

        comments = self.db.get_all('get_activity_comments', activity['activity_id'])
        for comment in comments:
            comment['timestamp'] = comment['timestamp'].isoformat()

        activity['comments'] = comments

        activity['flagged'] = self.has_flagged(uid, activity_id)



        return self.close_and_return(activity)

    def delete(self, uid, activity_id):
        record = self.db.get_one('get_user_activity', uid, activity_id)
        if record is None:
            return self.close_and_return({ 'error': 'access-denied'})
        
        activity = self.activity_from_record(record)

        self.db.execute('delete_activity', activity_id, uid)
        self.db.execute('clear_sharing_policy', activity_id)

        comments = self.db.get_all('get_activity_comments', activity['activity_id'])
        for comment in comments:
            comment['timestamp'] = comment['timestamp'].isoformat()

        activity['comments'] = comments
        activity['flagged'] = self.has_flagged(uid, activity_id)

        return self.close_and_return(activity)

    def set_sharing_policy(self, uid, activity_id, category, uids=[]):

        is_subscriber = self.subscriptions.isPayingUser(uid)

        record = self.db.execute('get_activity', activity_id)

        if record is None:
            return self.close_and_return({ 'error': 'does-not-exist' })

        activity = self.activity_from_record(record)

        if activity['uid'] is not uid:
            return self.close_and_return({ 'error': 'access-denied' })

        if category in ('all', 'friends', 'none'):
            self.db.execute('set_sharing_policy', activity_id, category)
        
        elif category is 'uids':
            if not is_subscriber:
                return self.close_and_return({ 'error': 'requires-subscription' })
            self.db.execute('clear_sharing_policy', activity_id)
            for uid in uids:
                self.db.execute('add_uid_to_sharing_policy', activity_id, uid)
        else:
            return self.close_and_return({ 'error': 'invalid-category' })

        activity['flagged'] = self.has_flagged(uid, activity_id)

        return self.close_and_return(activity)

    def get_sharing_policy(self, uid, activity_id):
        record = self.db.get_one('get_user_activity', uid, activity_id)
        if record is None:
            return self.close_and_return({ 'error': 'access-denied' })
        
        sharing = self.db.get_all('get_sharing_policy', activity_id)

        sharing_policy = []

        for policy in sharing:
            if policy['shared_with'] in ('all', 'none', 'friends'):
                sharing_policy = [policy['shared_with']]
            else:
                sharing_policy.append(policy['shared_with'])

        self.close_and_return({
            'sharing_policy': sharing_policy
        })

    def comment(self, uid, activity_id, message):
        has_access, activity = self.has_access(uid, activity_id)
        
        if activity is None:
            return self.close_and_return({ 'error': ('access-denied' if has_access is False else 'does-not-exist')})

        commentid = str( uuid.uuid1() )

        self.db.execute('comment_activity', commentid, activity_id, uid, message)

        activity['flagged'] = self.has_flagged(uid, activity_id)

        return self.close_and_return(activity)

    def update_comment(self, uid, commentid, message):
        record = self.db.get_one('get_comment', commentid)

        if uid is not commentid['uid']:
            return self.close_and_return({ 'error': 'access-denied' })
        
        self.db.execute('udpate_comment', message, commentid, uid)

        record['message'] = message
        record['timestamp'] = record['timestamp'].isoformat()

        return self.close_and_return(record)

    def delete_comment(self, uid, commentid):
        record = self.db.get_one('get_comment', commentid)
        if uid is not commentid['uid']:
            return self.close_and_return({ 'error': 'access-denied' })

        self.db.execute('delete_comment', commentid, uid)

        record['timestamp'] = record['timestamp'].isoformat()

        return self.close_and_return(record)
        
    def get_activity_chart(self, uid):
        days = list(self.db.get_all('get_activity_chart', uid))
        if len(days) is 0:
            days.append({
                "activities": 0,
                "date": (datetime.now() - timedelta(days=10)).strftime(DATE_FORMAT)
            })
        today_delta = (datetime.now() - datetime.strptime(days[-1]["date"], DATE_FORMAT)).days
        if len(days) > 0 and today_delta > 0:
            days.append({
                "activities": 0,
                "date": datetime.now().strftime(DATE_FORMAT)
            })


        filled_days = []

        for day in days:
            if len(filled_days) is 0:
                filled_days.append(day)
            else:
                old_date = datetime.strptime(filled_days[-1]["date"], DATE_FORMAT)
                new_date = datetime.strptime(day["date"], DATE_FORMAT)
                delta = new_date - old_date

                start = old_date if delta.days >= 0 else new_date
                end = new_date if delta.days >= 0 else old_date                
                
                for i in range(delta.days - 1):
                    working_date = start + timedelta(days=i + 1)
                    
                    filled_days.append({
                        "activities": 0,
                        "date": working_date.strftime(DATE_FORMAT)
                    })
                
                filled_days.append(day)
        filled_days.reverse()
        first_ten = filled_days[:10]
        first_ten.reverse()
        return self.close_and_return({
            'chart': first_ten
        })

    def flag(self, uid, activity_id):
        has_access, activity = self.has_access(uid, activity_id)
        if has_access is False:
            return self.close_and_return({ 'error': 'access-denied' })
        if activity is None:
            return self.close_and_return({ 'error': 'does-not-exist' })

        owner = activity['uid']

        self.db.execute('flag_activity', uid, activity_id, owner)

        activity['flagged'] = self.has_flagged(uid, activity_id)

        return self.close_and_return(activity)

    def unflag(self, uid, activity_id):
        has_access, activity = self.has_access(uid, activity_id)
        if has_access is False:
            return self.close_and_return({ 'error': 'access-denied' })
        if activity is None:
            return self.close_and_return({ 'error': 'does-not-exist' })
        
        self.db.execute('unflag_activity', uid, activity_id)

        activity['flagged'] = self.has_flagged(uid, activity_id)

        return self.close_and_return(activity)

    def get_announcements(self, uid):
        announcements = self.db.get_all('get_announcements', uid)
        return announcements

    def get_new_feed(self, uid, page):
        feed_items = self.db.get_all('get_feed', uid, 10, 10 * page)
        feed = []
        if page == 0:
            days = self.get_activity_chart(uid)
            chart = {
                'type': 'activity_chart',
                'chart': days['chart']
            }

            feed = [chart]

            announcements = self.get_announcements(uid)
            print(announcements)
            for announcement in announcements:
                announcement["type"] = "announcement"
                feed.append(announcement)

        for item in feed_items:

            records = self.db.get_all('get_activity_comments', item['activity_id'])

            for record in records:
                record['timestamp'] = record['timestamp'].isoformat()
            
            item['comments'] = records

            feed_item = {
                'type': 'activity',
                'activity': {
                    'activity_id': item['activity_id'],
                    'uid': item['uid'],
                    'type': item['type'],
                    'timestamp': item['timestamp'].isoformat(),
                    'data': json.loads( item['data'] ),
                    'date': item['date'],
                    'comments': item['comments']
                },
                'user': {
                    'uid': item['uid'],
                    'firstname': item['firstname'],
                    'lastname': item['lastname'],
                    'profileimage': item['profileimage'],
                    'streak': item['streak'],
                    'bio': item['bio']
                }
            }
            feed.append(feed_item)

        return self.close_and_return({
            'feed': feed
        })

    def add_image(self, uid, file):
        return self.file_storage.upload_to_activity_images(uid, file)

    