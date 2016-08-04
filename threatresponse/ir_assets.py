import boto3
import pickle
import json
import datetime
import uuid
import os
from tzlocal import get_localzone
from threatresponse.app import app
from threatresponse import controllers
from threatresponse.app import redis_store
from threatresponse import aws

##Celery Tasks
from threatresponse.tasks import delay_awsir
from threatresponse.tasks import delay_refresh_all_redis

def tzlocal():
    tz = get_localzone()
    return tz

def tzutc():
    tz = get_localzone()
    return tz

class Asset_Credential(object):
    def __init__(self, username=None, sshkey=None, instance_id=None):
        if None not in (username, sshkey, instance_id):
            self.username = username
            self.sshkey = sshkey
            self.instance_id = instance_id
            if self.is_cached():
                self.delete_credential()
                self.__serialize()
            elif instance_id is not None:
                self.__serialize()
        else:
            self.username = None
            self.sshkey = None
            self.instance_id = None

    def __serialize(self):
      controllers.pickle_object(
        (
            "credentials-{instance_id}"
        ).format(
            instance_id=self.instance_id
            )
        , self
    )

    def is_cached(self):
      if redis_store.get(
        ("credentials-{instance_id}").format(instance_id=self.instance_id)
        ):
          return True
      else:
          return False

    def exists(self, instance_id):
      if redis_store.get(
            ("credentials-{instance_id}").format(instance_id=instance_id)
        ):
          return True
      else:
          return False

    def delete_credential(self):
        redis_store.delete(
          ("credentials-{instance_id}").format(instance_id=self.instance_id)
          )

    def load_credential(self, instance_id):
        try:
            credential_object = pickle.loads(
                redis_store.get(
                    (
                        "credentials-{instance_id}"
                    ).format(
                        instance_id=instance_id
                        )
                    )
                )
        except:
            credential_object = super(Asset_Credential, self).__init__()
        return credential_object

class IR_Asset(object):
    def __init__(self):
        if self.is_cached() == True:
            self.asset_object = pickle.loads(redis_store.get('asset'))
            self.case_number = self.asset_object.case_number
            self.bucket = self.asset_object.bucket
            self.case_files = self.asset_object.case_files
            self.case_instances = self.asset_object.case_instances
        else:
            self.case_number = app.config.get('CASE_NUMBER')
            self.bucket = self.set_case_bucket()
            self.case_files = self.get_case_files()
            self.case_instances = self.get_case_instances()
            self.__serialize()

    def set_case_bucket(self):
        if redis_store.get('case_bucket') != None:
            return redis_store.get('case_bucket')
        else:
            case_bucket = controllers.set_case_bucket()
            return case_bucket

    def get_case_files(self):
        if len(redis_store.lrange('case_files', 0, -1)) > 0:
            return redis_store.lrange('case_files', 0, -1)
        else:
            files = controllers.enumerate_bucket(self.bucket)
            controllers.store_list_in_redis('case_files', files)
            return redis_store.lrange('case_files', 0, -1)
        pass

    def get_case_instances(self):
        if len(redis_store.lrange('case_instances', 0, -1)) > 0:
            return redis_store.lrange('case_instances', 0, -1)
        else:
            instances = controllers.populate_aws_processed_instances(self.case_number)
            controllers.store_list_in_redis('case_instances', instances)
            return redis_store.lrange('case_instances', 0, -1)
        pass

    def __serialize(self):
      controllers.pickle_object('asset', self)

    def refresh(self):
      self.case_number = app.config.get('CASE_NUMBER')
      self.bucket = self.set_case_bucket()
      self.case_files = self.get_case_files()
      self.case_instances = self.get_case_instances()
      print self.case_files
      redis_store.delete('asset')
      self.__serialize()

    def is_cached(self):
      if redis_store.get('asset') != None:
          return True
      else:
          return False

    def recently_launched_instances(self):
        s3 = boto3.resource('s3')
        recent_instances_file = ("{case_number}-recent_instances.log").format(case_number=self.case_number)
        s3.meta.client.download_file(self.bucket, recent_instances_file, ("/tmp/{recent_instances_file}").format(recent_instances_file=recent_instances_file))
        log = open(("/tmp/{recent_instances_file}").format(recent_instances_file=recent_instances_file))
        return log.read()

    def count_recently_launched_instances(self):
        recent_instances_file = ("{case_number}-recent_instances.log").format(case_number=self.case_number)
        try:
            log = open(("/tmp/{recent_instances_file}").format(recent_instances_file=recent_instances_file))
            lines = eval(log.read())
            return len(lines.keys())
        except:
            self.recently_launched_instances()
            log = open(("/tmp/{recent_instances_file}").format(recent_instances_file=recent_instances_file))
            lines = eval(log.read())
            return len(lines)

class Asset_Processor(object):
    def __init__(self):
        self.unprocessed = self.unprocessed_assets()

    def queue_asset(self, instance_id):
        assets = redis_store.lrange('unprocessed_instances', 0, -1)
        if not instance_id in assets:
            redis_store.lpush('unprocessed_instances', instance_id)

    def dequeue_asset(self, instance_id):
        redis_store.lrem('unprocessed_instances', -1, instance_id)

    def process_asset(self, instance_id, instance_inventory):
        credentials = Asset_Credential().load_credential(instance_id)
        if credentials is not None:
            user = credentials.username
            ssh_key_file = self.write_temporary_key(credentials.sshkey)
        else:
            user = "aws_ir_nobody"
            ssh_key_file = self.write_temporary_key("empty key")
        compromised_host_ip = instance_inventory[0]['public_ip_address']
        bucket = redis_store.get('case_bucket')
        case_number = app.config.get('CASE_NUMBER')
        delay_awsir.delay(
            case_number=case_number,
            bucket=bucket, user=user,
            ssh_key_file=ssh_key_file,
            compromised_host_ip=compromised_host_ip
        )

        #Async job to update case files in the background
        delay_refresh_all_redis.delay()
        pass

    def unprocessed_assets(self):
        try:
            assets = redis_store.lrange('unprocessed_instances', 0, -1)
            return assets
        except:
            return None

    def write_temporary_key(self, key):
        name = str(uuid.uuid4())[:8]
        path = ("/tmp/{name}.pem").format(name=name)
        key_file = open(path, 'w')
        key_file.write(key)
        key_file.close()
        os.chmod(path, 0600)
        return path

    def delete_temporary_key(self, path):
        os.remove(path)

class LogFile(object):
    def __init__(self):
        logfile_object = None
        self.assets = IR_Asset()

    def generate_filename(self, log_type, instance_id):
        case_number = self.assets.case_number
        filename = "{case_number}-{instance_id}-{log_type}.log".format(
            case_number=case_number,
            instance_id=instance_id,
            log_type=log_type
        )
        return filename

    def screenshot(self, instance_id):
        filename = "{case_number}-{instance_id}-{log_type}.jpg".format(
            case_number=self.assets.case_number,
            instance_id=instance_id,
            log_type='screenshot'
        )
        if self.exists(filename):
            return filename
        else:
            return None

    def console_log(self, instance_id):
        filename = self.generate_filename('console', instance_id)
        if self.exists(filename):
            return filename
        else:
            return None

    def acquisition_log(self, instance_id):
        filename = self.generate_filename('aws_ir', instance_id)
        if self.exists(filename):
            return filename
        else:
            return None

    def exists(self, file):
        case_files = IR_Asset().case_files
        if file in case_files:
            return True
        else:
            return False
