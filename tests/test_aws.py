import pytest
from ensure import ensure
from threatresponse import app
from threatresponse import aws


#we may want to checkout this tool for mocking boto
#https://github.com/spulec/moto

def test_client():
    connection = aws.Connect('us-west-2', 'ec2')
    assert connection.region is 'us-west-2'
    assert connection.service is 'ec2'
    assert connection.client is not None

    with pytest.raises(StandardError):
      connection = aws.Connect('tacostand', 'carnitas')

def test_regions():
  Region = aws.Region()
  ensure(Region.client).is_not_none()

  regions = Region.get_all()
  ensure(regions).contains('eu-west-1').also.contains('us-west-2')

def test_instance():
  Instance = aws.Instance()
  ensure(Instance.client).is_not_none()

def test_instance_running_by_region():
  Instance = aws.Instance()
  running_instances = Instance.get_running_by_region('us-west-2')
  print running_instances
  ensure(running_instances).is_nonempty()

  ensure.each_of(running_instances).has_keys([
    'public_ip_address',
    'instance_id',
    'launch_time',
    'platform',
    'vpc_id',
    'volume_ids'
    ])

def test_instance_all_instances():
  Instance = aws.Instance()
  running_instances = Instance.get_all_running()
  print "*******"
  print "*******"
  print "all running instances"
  print running_instances
  ensure(running_instances).is_nonempty()
