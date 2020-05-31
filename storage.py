from google.cloud import storage, vision
from google.protobuf import json_format

storage_client = storage.Client()
bucket_name = 'sac-storage-205890'

class Storage(object):

    # def create_bucket(self, bucket_name):
    #     storage_client.create_bucket(bucket_name)
    #     return f'Created bucket {bucket_name}'

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

    # def get_text(self, bucket_name, prefix, types):
    #     bucket = storage_client.bucket(bucket_name)
    #     blob_list = list(bucket.list_blobs(prefix=prefix))

    #     fulltext = ''
        
    #     for blob in blob_list:
    #         json_string = blob.download_as_string()
    #         response = json_format.Parse(json_string, types)

    #         for page in response.responses:
    #             fulltext += page.full_text_annotation.text

    #     return fulltext