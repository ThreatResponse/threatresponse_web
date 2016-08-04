import os
import boto3
import pickle
import collections

from threatresponse.app import redis_store
from threatresponse import app
from threatresponse import dockeraction
from threatresponse import controllers
from threatresponse import settings
from threatresponse.tasks import delay_refresh_all_redis


from awsthreatprep import checker

class Connect(object):
    def __init__(self, region='us-west-2', service='ec2'):
        self.region = region
        self.service = service

        try:
          self.client = boto3.client(service,region)
        except:
          raise StandardError(
            "No AWS Credentials could be found."
          )

class Region(object):
  def __init__(self):
    self.client = Connect().client

  def get_all(self):
    availRegions = []
    regions = self.client.describe_regions()
    for region in regions['Regions']:
        availRegions.append(region['RegionName'])
    return availRegions

class ThreatResponseAMI(object):
    def __init__(self):
        self.ami_ids = settings.AMI_IDS
        print self.ami_ids


class Advisor(object):
    def __init__(self):
        if self.is_cached() == True:
            self.advisor_object = pickle.loads(redis_store.get('advisor'))
            self.results = self.advisor_object.results
        else:
            self.results = self.json()
            self.__serialize()

    def json(self):
        c = checker.Checker()
        c.run_checks()
        return c.results_dict

    def __serialize(self):
        controllers.pickle_object('advisor', self)

    def is_cached(self):
        if redis_store.get('advisor'):
            return True
        else:
            return False

class Instance(object):
  def __init__(self):
    self.client = Connect().client

  def get_running_by_region(self, region):
    inventory = []

    reservations = Connect(region).client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )['Reservations']

    for reservation in reservations:
      for instance in reservation['Instances']:
          instance_data = self.__extract_data(instance)
          instance_data['region'] = region
          inventory.append(instance_data)

    return inventory

  def get_processed_by_region(self, region):
    inventory = []

    reservations = Connect(region).client.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['stopped']},
                {'Name': 'tag:cr-case-number', 'Values': [app.config.get('CASE_NUMBER')]}
            ])['Reservations']

    for reservation in reservations:
      for instance in reservation['Instances']:
          instance_data = self.__extract_data(instance)
          instance_data['region'] = region
          inventory.append(instance_data)

    return inventory

  def __extract_data(self, instance):
    return dict(
      public_ip_address = instance.get('PublicIpAddress', None),
      instance_id = instance['InstanceId'],
      launch_time = instance['LaunchTime'],
      platform = instance.get('Platform', None),
      vpc_id = instance['VpcId'],
      ami_id = instance['ImageId'],
      volume_ids = [ bdm['Ebs']['VolumeId'] for bdm in instance.get('BlockDeviceMappings', [] ) ],
      )

  def get_all_running(self):
    inventory = {}

    for region in Region().get_all():
      inventory[region] = self.get_running_by_region(region)

    return inventory

  def get_all_processed(self):
    inventory = {}

    for region in Region().get_all():
      inventory[region] = self.get_processed_by_region(region)

    return inventory

class Inventory(object):
  def __init__(self):
    if self.is_cached() == True:
        self.inventory_object = pickle.loads(redis_store.get('inventory'))
        self.regions = self.inventory_object.regions
        self.instances = self.inventory_object.instances
        self.processed_instances = self.inventory_object.processed_instances
    else:
        self.regions = Region().get_all()
        self.instances = Instance().get_all_running()
        self.processed_instances = Instance().get_all_processed()
        self.__serialize()

  def __serialize(self):
      controllers.pickle_object('inventory', self)

  def refresh(self):
      self.regions = Region().get_all()
      self.instances = Instance().get_all_running()
      self.processed_instances = Instance().get_all_processed()
      redis_store.delete('inventory')
      self.__serialize()

  def is_cached(self):
      if redis_store.get('inventory'):
          return True
      else:
          return False

  def count_by_region(self):
    list = []
    inventory = self.instances
    for region in inventory:
        count = 0
        for instance in inventory[region]:
            count = count + 1
        list.append({region : count})
    return list

  def count_ami_by_type(self):
    instance_list = [x for region in list(self.instances.values()) for x in region if region != []]
    ami_counts = collections.Counter([x['ami_id'] for x in instance_list])
    return ami_counts

  def count(self):
    inventory = self.instances
    count = 0
    for region in inventory:
      for instance in inventory[region]:
          count = count + 1
    return count

  def volumes_by_instance(self):
    instances = self.processed_instances
    list_by_instance = []
    for region in instances:
        if instances[region] is not None:
            for instance in instances[region]:
                list_by_instance.append({'id': instance['instance_id'], 'volumes':instance['volume_ids']})
    return list_by_instance

  def search(self, query):
      list = []
      for region in self.instances:
          for instance in self.instances[region]:
              if query in instance.values():
                  list.append(instance)
      return list

class S3Action(object):
    def __init__(self):
        self.s3 = boto3.resource('s3')
        self.case_bucket = redis_store.get('case_bucket')
        self.client = boto3.client('s3', 'us-west-2')

    def bytesto(self, bytes_in, to, bsize=1024):
        a = {'k' : 1, 'm': 2, 'g' : 3, 't' : 4, 'p' : 5, 'e' : 6 }
        r = float(bytes_in)
        for i in range(a[to]):
            r = r / bsize

        return(int(r))

    def download_to_temp(self, filename):
        self.s3.meta.client.download_file(
          self.case_bucket, filename,
          ("/tmp/{filename}").format(filename=filename)
        )

    def download_to_volatility(self, filename):
        self.s3.meta.client.download_file(
            self.case_bucket, filename,
            ("tmp/{filename}").format(
                filename=filename
                )
            )

    def streaming_download(self, filename):
        result = self.s3.meta.client.download_file(
            self.case_bucket,
            filename,
            "/tmp/{filename}".format(
                filename=filename
                )
            )
        return result

    def get_size(self, filename):
        try:
            object_summary = self.s3.ObjectSummary(self.case_bucket,filename)
            return self.bytesto(bytes_in=object_summary.size, to='m')
        except:
            return "Size Unknown"

    def create_date(self, filename):
        try:
            object_summary = self.s3.ObjectSummary(self.case_bucket,filename)
            return object_summary.last_modified
        except:
            return "Date Unknown"

class Snapshot(object):
  def __init__(self):
    iam_client = boto3.client('iam')
    iam = boto3.resource('iam')
    if self.is_cached() == True:
        self.snapshot_object = pickle.loads(redis_store.get('snapshots'))
        self.regions = self.snapshot_object.regions
        self.snapshots = self.snapshot_object.snapshots
    else:
        self.regions = Region().get_all()
        self.snapshots = self.get_case_snapshots()
        self.__serialize()

  def get_snapshots_by_region(self, region):
      inventory = []
      snapshots = Connect(region).client.describe_snapshots(
              Filters=[
                  {'Name': 'tag:cr-case-number', 'Values': [app.config.get('CASE_NUMBER')]}
              ])['Snapshots']
      for snapshot in snapshots:
        snapshot_data = self.__extract_data(snapshot)
        snapshot_data['region'] = region
        inventory.append(snapshot_data)
      return inventory

  def __serialize(self):
      controllers.pickle_object('snapshots', self)

  def __extract_data(self, snapshot):
      return dict(
        id = snapshot.get('SnapshotId', None),
        description = snapshot.get('Description', None),
        VolumeId = snapshot['VolumeId'],
        create_time = snapshot['StartTime'],
        volume_size = snapshot['VolumeSize']
        )

  def get_case_snapshots(self):
    inventory = {}
    for region in Region().get_all():
      inventory[region] = self.get_snapshots_by_region(region)
    return inventory

  def is_cached(self):
      if redis_store.get('snapshots'):
          return True
      else:
          return False

  def mark_processed(self, snapshot_id):
      redis_store.lpush("case_processed_snapshots", snapshot_id)

  def is_processed(self, snapshot_id):
      processed_snapshots = redis_store.lrange("case_processed_snapshots", 0 ,-1)
      if snapshot_id in processed_snapshots:
          return True
      else:
          return False

  def launch_processor(self, snapshot_id, region):
    client = Connect(region=region).client
    ec2_resource = boto3.resource('ec2', region)
    bucket = redis_store.get('case_bucket')
    script = """#!/bin/bash
    mkdir -p /tmp/plaso
    for i in $(lsblk -r |awk '{ print $1 }'|grep -v md | grep -v docker | grep -v xvda |grep -v loop |grep .*[[:digit:]]|sort|uniq;);
      do
      echo $i
        docker run --privileged --env SNAP=SNAPSHOT_ID -v /dev/$i:/dev/$i -v /tmp:/tmp threatresponse/plaso > /tmp/plaso/SNAPSHOT_ID.log;
      done

    while [ `docker ps | grep plaso | cut -d ' ' -f1 | wc -l` == '1' ]
    do
      echo "Plaso running"
    done
        aws s3 sync /tmp/plaso/ s3://BUCKETNAME_HERE

	sleep 60
    poweroff
	"""
    script = script.replace('BUCKETNAME_HERE', bucket)
    script = script.replace('SNAPSHOT_ID', snapshot_id)

    instance = ec2_resource.create_instances(
		ImageId=ThreatResponseAMI().ami_ids[region],
		MinCount=1,
		MaxCount=1,
        #KeyName='YOUR-DEBUGGING-KEY',
		InstanceType='m3.large',
		IamInstanceProfile={
                        'Name': "cloudresponse_workstation-{case_number}-{region}".format(
                            case_number=app.config.get('CASE_NUMBER'),
                            region=region
                        )
                },
		InstanceInitiatedShutdownBehavior='terminate',
	        BlockDeviceMappings=[
		{
		    'VirtualName': 'ephemeral1',
		    'DeviceName': '/dev/sdf',
		    'Ebs': {
			'SnapshotId': snapshot_id,
			'DeleteOnTermination': True,
			'VolumeType': 'gp2',
		    },
		},
	    ],
	        UserData=script
	)
    instance_id = str(instance[0]).split('=')[1].rstrip(')').split('\'')[1].rstrip('\'')

    redis_store.set(snapshot_id, 'processing')
    client.create_tags(
        Resources=[
            instance_id
        ],
        Tags=[
            {'Key': 'snapshot-processor','Value': "{snapshot_id}".format(snapshot_id=snapshot_id)}
        ]
    )
    delay_refresh_all_redis.delay()
    return instance_id

  def snapshots_by_volume_id(self):
      snapshots = self.snapshots
      list_by_volume = []
      for region in snapshots:
          if snapshots[region] is not None:
              for snapshot in snapshots[region]:
                  list_by_volume.append({'id': snapshot['id'], 'volume':snapshot['VolumeId']})
      return list_by_volume

  def volume(self, snapshot_id):
      snapshots = self.snapshots_by_volume_id()
      for snapshot in snapshots:
          if snapshot['id'] == snapshot_id:
              return snapshot['volume']

  def instance(self, snapshot_id):
      inventory = Inventory().volumes_by_instance()
      snapshot_volume = self.volume(snapshot_id)
      for instance in inventory:
          if snapshot_volume in instance['volumes']:
              return instance
      return None

  def search_case_files(self, snapshot_id):
      case_files = controllers.enumerate_bucket(redis_store.get('case_bucket'))
      plaso_file = "{snapshot_id}.plaso".format(snapshot_id=snapshot_id)
      if plaso_file in case_files:
         return True
      else:
         return False

  def has_plaso(self, snapshot_id):
      if (self.search_case_files(snapshot_id)):
          redis_store.set(snapshot_id, "complete")
          return True
      else:
          return False

  def in_progress(self, snapshot_id):
      if redis_store.get(snapshot_id) == "processing":
          return True
      else:
          return False

  def is_timesketch(self, snapshot_id):
      if redis_store.get(snapshot_id) == "timesketch":
          return True
      else:
          return False

  def snapshot_state(self, snapshot_id):
      if redis_store.get(snapshot_id) is None:
          self.has_plaso(snapshot_id)
      return redis_store.get(snapshot_id)

  def timesketch(self, snapshot_id):
      if self.has_plaso(snapshot_id):
          plaso_file = "{snapshot_id}.plaso".format(snapshot_id=snapshot_id)
          S3Action().download_to_temp(plaso_file)
          ts = dockeraction.TimeSketchControl()
          ts.import_plaso_file(plaso_file)
          redis_store.set(snapshot_id, "timesketch")
      else:
          pass

class MemoryDumps(object):
    def __init__(self):
        self.case_files = controllers.enumerate_bucket(redis_store.get('case_bucket'))
        self.memory_files = self.lime_files()

    def lime_files(self):
        list = []
        for asset in self.case_files:
            if asset.endswith('.lime'):
                list.append(asset)
        return list

    def on_disk(self, lime_file):
        return os.path.exists("tmp/{lime_file}".format(lime_file=lime_file))
