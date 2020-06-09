from google.cloud import firestore

db = firestore.Client(project='sac-passport-205890')

class Firestore(object):

    def check_info(self, filename):
        info_ref = info_ref = db.collection(u'passport').document(filename)
        return info_ref.get().exists

    def get_info(self, filename):
        info_ref = db.collection(u'passport').document(filename)
        info = info_ref.get()
        if info.exists:
            return info.to_dict()
        else:
            return None

    def save_info(self, filename, fields, labels):
        info_ref = db.collection(u'passport').document(filename)
        if info_ref.get().exists:
            return None
        else:
            info_ref.set(fields)
            info_ref.update({'labels':labels})
            return 'Success'

    def del_info(self, filename):
        info_ref = db.collection(u'passport').document(filename)
        if info_ref.get().exists:
            info_ref.delete()

    def get_status(self, filename):
        staus_ref = db.collection(u'status').document(filename)
        status = staus_ref.get()
        if stats.exists:
            return status.to_dict()['status']
        else:
            return None
    
    def save_status(self, filename, status):
        status_ref = db.collection(u'status').document(filename)
        status_ref.set({'status':status})
        return 'Success'

    def all_status(self):
        status_ref = db.collection(u'status').order_by(u'timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
        status = {}
        for cur in status_ref:
            status[cur.id] = cur.to_dict()['status']
        
        return status

    def del_status(self):
        stats_ref = db.collection(u'status').stream()
        for status in stats_ref:
            status.reference.delete()