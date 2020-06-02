def batch_passport(event, context):
    from google.cloud import firestore
    db = firestore.Client(project='sace-passport-205890')

    if 'attributes' in event:
        if 'files' in event['attributes']:
            filenames = event['attributes']['files']

            for filename in filenames:
                passport_ref = db.collection(u'passport').document(filename)
                #TODO: ricopia la lista di operazioni prese da prima, ed eventualemnte la pubblicazione del procedimento del processo, con una percentuale, oppure con 4 su 15 fatti per esempio
        else:
            filenames = None
            print('Nothing done')