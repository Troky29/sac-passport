def batch_passport(event, context):
    from google.cloud import firestore
    from requests import get
    db = firestore.Client(project='sac-passport-205890')

    basePath = 'https://api-dot-sac-passport-205890.nw.r.appspot.com/api/v1'

    if 'attributes' in event:
        if 'filenames' in event['attributes']:
            filenames = event['attributes']['filenames']

            print(f'filenames {filenames}')

            for filename in filenames.split():
                print(filename)
                ret = get(f'{basePath}/passport/{filename}')
            
                result = ret.json()
                code = ret.status_code

                print(code)

                #TODO: send error message
                if code != 200: 
                    print(code)
                    continue

                #TODO: altro messaggio di errore
                labels = result['labels']
                if all(label['label'] != 'Identity document' for label in labels): 
                    print('Not identity documents')
                    continue

                fields = result['fields']

                passport_ref = db.collection(u'passport').document(filename)
                passport_ref.set(fields)
                #TODO: messaggio di completamento
    else:
        filenames = None
        print('Nothing done')