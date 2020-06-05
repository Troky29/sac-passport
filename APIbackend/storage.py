from google.cloud import storage

storage_client = storage.Client()
bucket_name = 'sac-storage-205890'

class Storage(object):

    def upload_document(self, my_file, blob_name):
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(my_file)
        return f'Uploaded {blob_name} succesfully'

    def get_document(self, blob_name):
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        if blob.exists():
            return blob.download_as_string()
        else:
            return None

    def delete_document(self, blob_name):
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if blob.exists():
            blob.delete()

    def check_document(self, blob_name):
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()