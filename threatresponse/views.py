import os

import flask
from flask import jsonify, request
from threatresponse.app import app
from threatresponse import models
from threatresponse import utils
from threatresponse import controllers
from datetime import datetime
from threatresponse.app import redis_store

import aws
import ir_assets



@app.route('/')
@app.route('/index.html')
def home():

    asset = ir_assets.IR_Asset()
    assets = ir_assets.Asset_Processor()
    inventory = aws.Inventory().instances
    inventory_count = aws.Inventory().count()
    ami_count = aws.Inventory().count_ami_by_type()
    region_count = aws.Inventory().count_by_region()
    return flask.render_template('home.html',
        inventory=inventory,
        asset=asset,
        assets=assets,
        inventory_count=inventory_count,
        countbyregion=region_count,
        ami_count=ami_count
    )

@app.route('/advise')
def advise():
    return flask.render_template('advise.html')

@app.route('/acquire')
def acquire():
    instance = request.args.get('instance-search') or ''
    return flask.render_template('acquire.html',
      instance=instance
    )

@app.route('/analyze')
def analyze():
    asset = ir_assets.IR_Asset()
    snapshots = aws.Snapshot()
    if request.args.get('view'):
        views = request.args.get('view')
        if 'disks' in views:
            return flask.render_template(
                'analyze.html',
                 disks=True,
                 asset=asset,
                 snapshots=snapshots
            )
        if 'logs' in views:
            asset = ir_assets.IR_Asset()
            logfile = ir_assets.LogFile()
            inventory = aws.Inventory()
            return flask.render_template(
                'analyze.html',
                 logs=True,
                 asset=asset,
                 logfile=logfile,
                 inventory=inventory
            )
        if 'memory' in views:
            memory_dumps = aws.MemoryDumps()
            file_actions = aws.S3Action()
            return flask.render_template(
                'analyze.html',
                 memory=True,
                 asset=asset,
                 file_actions=file_actions,
                 memory_dumps=memory_dumps
            )
        if 'all' in views:
            return flask.render_template(
                'analyze.html',
                 disks=True,
                 logs=True,
                 memory=True,
                 asset=asset,
                 snapshots=snapshots
            )
    return flask.render_template(
        'analyze.html',
         asset=asset,
         snapshots=snapshots
    )

@app.route('/mitigate')
def mitigate():
    assets = ir_assets.Asset_Processor()
    credentials = ir_assets.Asset_Credential()
    inventory = []
    for asset in assets.unprocessed_assets():
        inventory.append(aws.Inventory().search(asset)[0])

    return flask.render_template('mitigate.html',
        assets=assets, credentials=credentials, inventory=inventory
    )

@app.route('/credentials/<instance_id>', methods=['GET', 'POST'])
def add_credentials(instance_id):
    if request.method == 'POST':
        username =  request.form["username"]
        key =  request.form["key"]
        instance_id =  request.form["instance_id"]
        credential = ir_assets.Asset_Credential(username, key, instance_id)
        return flask.render_template('_acquire-credential-modal.html',
            instance_id=instance_id, credential=credential
            )
    if request.method == 'GET':
        try:
            credential = ir_assets.Asset_Credential().load_credential(instance_id)
        except:
            credential = None
        return flask.render_template('_acquire-credential-modal.html',
            instance_id=instance_id, credential=credential
            )


def inventory_fixture():
  return dict(
      us_west_2 = [
        dict(
          public_ip_address = '54.149.115.211',
          instance_id = 'i-b692416d',
          launch_time = datetime(2016, 6, 9, 17, 30, 14),
          platform = None,
          vpc_id = 'vpc-8b0b89e0',
          volume_ids = ['vol-a1330113'],
          region = 'us-west-2'
          ),
        dict(
          public_ip_address = '54.191.156.219',
          instance_id = 'i-fc609053',
          launch_time = datetime(2016, 6, 9, 17, 30, 14),
          platform = None,
          vpc_id = 'vpc-8b0b89e0',
          volume_ids = ['vol-a93b071f'],
          region = 'us-west-2'
          )
        ]
      )
