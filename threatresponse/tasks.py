"""Celery task for processing aws_ir jobs"""

import os
import sys
import boto3
import urllib2
from aws_ir import aws_ir
from threatresponse.app import create_celery_app

celery = create_celery_app()

@celery.task()
def delay_awsir(
            case_number,
            bucket,
            user,
            ssh_key_file,
            compromised_host_ip
        ):
        mitigation_attempt = HostCompromise(
                    case_number=case_number,
                    bucket=bucket, user=user,
                    ssh_key_file=ssh_key_file,
                    compromised_host_ip=compromised_host_ip
                )
        print compromised_host_ip
        mitigation_attempt.mitigate()

@celery.task()
def delay_refresh_all_redis():
    response = urllib2.urlopen(
        'http://127.0.0.1:9999/api/inventory?type=refresh'
    )
    html = response.read()

@celery.task()
def download_memory_to_temp(filename, bucket):
    s3 = boto3.resource('s3')
    s3.meta.client.download_file(bucket, filename, ("tmp/{filename}").format(filename=filename))

@celery.task()
def download_logs_to_temp(filename, bucket):
    s3 = boto3.resource('s3')
    s3.meta.client.download_file(bucket, filename, ("tmp/{filename}").format(filename=filename))
