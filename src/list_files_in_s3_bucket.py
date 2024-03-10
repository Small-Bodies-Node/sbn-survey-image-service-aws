
import boto3


def list_files_in_s3_bucket(bucket_name):
    """
        List all files in a given S3 bucket.
        Used for local debugging
    """
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    print('<><><><><>')
    for obj in bucket.objects.all():
        print(obj.key)
    print('<><><><><>')
