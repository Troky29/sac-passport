def batch_passport(event, context):
    from google.cloud import firestore
    from requests import get
    from google.cloud import pubsub_v1

    db = firestore.Client(project='sac-passport-205890')
    project_id = 'sac-passport-205890'
    topic_name = 'operation-result'

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    basePath = 'https://api-dot-sac-passport-205890.nw.r.appspot.com/api/v1'

    if 'attributes' in event:
        if 'filenames' in event['attributes']:
            filenames = event['attributes']['filenames']

            for filename in filenames.split():
                ret = get(f'{basePath}/passport/{filename}')
            
                result = ret.json()
                code = ret.status_code

                if code != 200:
                    publisher.publish(topic_path, filename.encode('ascii'), status=(f'ERROR: {code}, {result}').encode('ascii'))
                    continue

                labels = result['labels']
                if 'Identity document' not in labels:
                    publisher.publish(topic_path, filename.encode('ascii'), status=b'ERROR: Not a passport')
                    continue

                fields = result['fields']
                # fields = {}
                # for field in result['fields']: fields[field['field']] = field['value']
                # print(fields)

                passport_ref = db.collection(u'passport').document(filename)
                passport_ref.set(fields)
                
                publisher.publish(topic_path, filename.encode('ascii'), status=b'DONE')
    else:
        filenames = None
        print('Nothing done')

if __name__ == "__main__":
    batch_passport({"message":"Contenuto del messaggio", 
    "attributes":{"filenames":"fa9b8499-ee06-4197-9f06-7de342bb7d3aBill_Passport.JPG"}}, None)