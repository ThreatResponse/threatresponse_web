import boto3
import pytest
import argparse
import mock
import moto
import os
import time

from threatresponse import tasks
from threatresponse import settings


def launch_test_machine(region='us-west-2'):
    client =  boto3.client('ec2', region)
    ec2_resource = boto3.resource('ec2', region)
    try:
        kp = ec2_resource.KeyPair("integration-test-key")
        kp.delete()
    except:
        pass

    keypair = client.create_key_pair(KeyName="integration-test-key")
    f = open('/tmp/integration.test-key.pem','w')
    f.write(keypair['KeyMaterial'])
    f.close()


    instance = ec2_resource.create_instances(
        ImageId=settings.AMI_IDS['us-west-2'],
        MinCount=1,
        MaxCount=1,
        InstanceType='m3.large',
        InstanceInitiatedShutdownBehavior='terminate',
        KeyName="integration-test-key"

    )

    instance_id = str(instance[0]).split('=')[1].rstrip(')').split('\'')[1].rstrip('\'')
    print instance[0].public_ip_address
    kp = ec2_resource.KeyPair("integration-test-key")
    kp.delete()
    client.create_tags(
        Resources=[
            instance_id
        ],
        Tags=[
              {'Key': 'Name','Value': "test-launch-ir-process"}
         ]
    )

    time.sleep(30)


    return

def test_setup_workstation():
    client =  boto3.client('ec2', 'us-west-2')
    #instance = launch_test_machine()
    reservations = client.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'tag:Name', 'Values': ['test-launch-ir-process']}
            ])['Reservations']
    ip_address = reservations[0]['Instances'][0]['PublicIpAddress']
    while ip_address == None:
        reservations = client.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['running']},
                    {'Name': 'tag:Name', 'Values': ['test-launch-ir-process']}
                ])['Reservations']
        ip_address = reservations[0]['Instances'][0]['PublicIpAddress']


    #tasks.delay_awsir.delay(
    #    'cr-16-071619-cdd5',
    #    'cloud-response-8c60cf6a38df454da26772df4976ded3',
    #    'ec2-user',
    #    '/tmp/integration.test-key.pem',
    #    ip_address
    #)
    pass

def teardown():
    try:
        client =  boto3.client('ec2', 'us-west-2')
        ec2_resource = boto3.resource('ec2', 'us-west-2')
        kp = ec2_resource.KeyPair("integration-test-key")
        kp.delete()
        #os.remove('/tmp/integration.test-key.pem')
    except:
        pass
