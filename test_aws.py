# test_s3_upload.py
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_S3_REGION_NAME', 'eu-north-1')
)

# Test upload
try:
    s3.put_object(
        Bucket='ch-blog-media',
        Key='test.txt',
        Body=b'Hello World',
        ContentType='text/plain'
    )
    print("✅ Upload successful!")
    
    # Test download
    response = s3.get_object(Bucket='ch-blog-media', Key='test.txt')
    print("✅ Download successful:", response['Body'].read())
    
    # Test public URL
    url = f"https://ch-blog-media.s3.eu-north-1.amazonaws.com/test.txt"
    print("✅ Public URL:", url)
    
except Exception as e:
    print("❌ Error:", e)