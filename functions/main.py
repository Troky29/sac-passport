def batch_passport(event, context):
    from google.cloud import firestore
    from requests import get
    # from google.cloud import pubsub_v1

    db = firestore.Client(project='sac-passport-205890')
    # project_id = 'sac-passport-205890'
    # topic_name = 'operation-result'

    # publisher = pubsub_v1.PublisherClient()
    # topic_path = publisher.topic_path(project_id, topic_name)

    basePath = 'https://api-dot-sac-passport-205890.nw.r.appspot.com/api/v1'

    if 'attributes' in event:
        if 'filenames' in event['attributes']:
            filenames = event['attributes']['filenames'].split()

            status_ref = db.collection(u'status')
            [status_ref.document(filename).set({'status':'WAITING', 'timestamp':firestore.SERVER_TIMESTAMP}) for filename in filenames]
            
            for filename in filenames:
                # publisher.publish(topic_path, filename.encode('ascii'), status=b'RUNNING')
                file_status = status_ref.document(filename)
                file_status.update({'status':'RUNNING'})

                ret = get(f'{basePath}/passport/{filename}')
            
                result = ret.json()
                code = ret.status_code

                if code != 200:
                    file_status.update({'status':f'ERROR {code}: {result}'})
                    # publisher.publish(topic_path, filename.encode('ascii'), status=(f'ERROR: {code}, {result}').encode('ascii'))
                    continue

                labels = result['labels']
                if 'Identity document' not in labels:
                    file_status.update({'status':f'ERROR {code}: Not a passport'})
                    # publisher.publish(topic_path, filename.encode('ascii'), status=b'ERROR: Not a passport')
                    continue
                
                file_status.update({u'status':'DONE'})
                # publisher.publish(topic_path, filename.encode('ascii'), status=b'DONE')
    else:
        filenames = None
        print('Nothing done')
