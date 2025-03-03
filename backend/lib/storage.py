from dotenv import load_dotenv
import boto3
import os
import datetime

load_dotenv()

class Storage:
    def __init__(self):
        self.client = boto3.client('s3',
            endpoint_url='https://ams3.digitaloceanspaces.com',
            aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
            region_name='ams3'
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')

    def upload_text(self, text: str, key: str, public: bool = False):
        self.client.put_object(Bucket=self.bucket_name, Key=key, Body=text, ACL='public-read' if public else 'private', ContentType='text/plain')

    def upload_file(self, file_path: str, key: str, public: bool = False):
        self.client.upload_file(file_path, self.bucket_name, key, ExtraArgs={'ACL': 'public-read' if public else 'private'})
        
    def download_file(self, key: str, file_path: str):
        self.client.download_file(self.bucket_name, key, file_path)

    def download_text(self, key: str) -> str:
        return self.client.get_object(Bucket=self.bucket_name, Key=key)['Body'].read().decode('utf-8')

    def list_files(self, prefix: str = None) -> list[str]:
        return self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)['Contents']
    
    def get_file_last_modified(self, key: str) -> datetime.datetime:
        return self.client.head_object(Bucket=self.bucket_name, Key=key)['LastModified']
