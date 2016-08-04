import os
REDIS_URL = "redis://{ip}:6379:/0".format(ip=os.environ.get('REDIS_PORT_6379_TCP_ADDR', 'localhost'))
CELERY_BROKER_URL="redis://{ip}:6379:/".format(ip=os.environ.get('REDIS_PORT_6379_TCP_ADDR', 'localhost'))
CELERY_RESULT_BACKEND="redis://{ip}:6379:/0".format(ip=os.environ.get('REDIS_PORT_6379_TCP_ADDR', 'localhost'))
TIMESKETCH_URL="http://timesketch:5000"
AMI_IDS = { 'us-west-2' : 'ami-4c07c52c', 'us-west-1' : 'ami-e3c88e83', 'us-east-1' : 'ami-bc49cbab' }
