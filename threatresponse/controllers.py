import base64
import flask
import re
import urllib
import boto3
import pickle

from threatresponse.app import app
from threatresponse import models
from threatresponse import utils
from threatresponse.app import redis_store


def set_case_bucket():
    s3 = boto3.resource('s3')
    buckets = s3.buckets.all()
    for bucket in buckets:
      if bucket.name.startswith("cloud-response-"):
          tags = get_bucket_tags(bucket.name)
          if check_bucket_tag(tags):
              case_bucket = bucket.name
              redis_store.set('case_bucket', case_bucket)
              return case_bucket
          else:
              pass
      else:
          pass

def get_bucket_tags(bucket):
    try:
        s3 = boto3.client('s3')
        response = s3.get_bucket_tagging(
            Bucket=bucket,

        )
    except:
        response = None
    return response

def check_bucket_tag(tag_object):
    for tag in tag_object['TagSet']:
        if tag['Value'] == app.config.get('CASE_NUMBER'):
           return True
        else:
           return False

def enumerate_bucket(bucket):
    try:
        files = []
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket)
        for obj in bucket.objects.all():
            files.append(obj.key)
        return files
    except:
        return None

### Currently used in index view to solve a cross linking problem between IR_Asset and AWS Class
def get_aws_regions(connection_object=None):
    if connection_object == None:
        connection_object = get_aws_client()
    try:
        availRegions = []
        regions = connection_object.describe_regions()
        for region in regions['Regions']:
            availRegions.append(region['RegionName'])
        return availRegions
    except:
        raise StandardError(
            "No AWS Credentials could be found."
)

### Currently used in index view to solve a cross linking problem between IR_Asset and AWS Class
def get_aws_client(region='us-west-2', service='ec2'):
    try:
        client = boto3.client(
            service,
            region_name=region
        )
        return client
    except:
        raise StandardError(
            "No AWS Credentials could be found."
)

def populate_aws_processed_instances(case_number):
    connection_object = get_aws_client()
    inventory = []
    regions = get_aws_regions()
    region_instances = {}

    for region in regions:
        instances_list = [x["Instances"] for x in get_aws_client(region=region).describe_instances(
            Filters=[{'Name': 'tag-value', 'Values': [case_number]}, {'Name': 'instance-state-name', 'Values': ['stopped']}]
            )['Reservations']]
        print instances_list
    if (len(instances_list) > 0):
        for instances_iteritems in instances_list:
            region_instances[region] = instances_iteritems

            for region,instances in region_instances.iteritems():
                for instance in instances:
                    inventory.append(dict(
                        public_ip_address=instance.get('PublicIpAddress',None),
                        instance_id=instance['InstanceId'],
                        launch_time=instance['LaunchTime'],
                        platform=instance.get('Platform', None),
                        vpc_id=instance['VpcId'],
                        volume_ids = [ bdm['Ebs']['VolumeId'] for bdm in instance.get('BlockDeviceMappings', [] ) ],
                        region=region
                        ))
    return inventory

def store_list_in_redis(list_key, list_data):
    for list_item in list_data:
        print list_item
        redis_store.lpush(list_key, list_item)
    pass

def pickle_object(key, original_object):
    pickled_object = pickle.dumps(original_object)
    try:
        redis_store.set(key, pickled_object)
        return True
    except:
        return False

def unpickle_object(key):
    try:
        print unpickling
        unpickled_object = pickle.loads(redis_store.get(key))
        return unpickled_object
    except:
        print "exception unpickling"
        return None
