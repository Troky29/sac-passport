def batch_passport(event, context):
    from google.cloud import firestore
    from requests import get
    db = firestore.Client(project='sac-passport-205890')

    basePath = 'http://127.0.0.1:5000/api/v1'

    if 'attributes' in event:
        if 'filenames' in event['attributes']:
            filenames = event['attributes']['filenames']

            for filename in filenames.split():
                ret = get(f'{basePath}/passport/{filename}')
                result = ret.json()
                code = ret.status_code
                passport = {}

                #TODO: send error message
                if code != 200: continue
                
                #TODO: altro messaggio di errore
                labels = result['labels']
                if all(label['label' != 'Identity document'] for label in labels): continue

                fields = result['fields']
                for field in fields: passport[field['field']] = field['value']

                passport_ref = db.collection(u'passport').document(filename)
                passport_ref.set(passport)
                #TODO: messaggio di completamento
    else:
        filenames = None
        print('Nothing done')