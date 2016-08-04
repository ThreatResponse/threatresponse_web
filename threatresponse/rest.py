import os
import json
import pytz
import flask
import hashlib
import datetime
from operator import add
from itertools import chain

from flask.ext import restful
from flask.ext.restful import fields

from flask import request
from flask import send_file
from flask import jsonify, request

from threatresponse.app import app
from threatresponse.app import redis_store
from threatresponse import controllers
from threatresponse import models
from threatresponse import utils
from threatresponse import aws
from threatresponse import ir_assets

from awsthreatprep import checker

api = restful.Api(app)

@app.route('/api/advisor')
def advisor():
    results = aws.Advisor().results
    return jsonify(results=results)

@app.route('/search')
def search():
    query = request.args.get('search')
    results = aws.Inventory().search(query)
    process_queue = ir_assets.Asset_Processor().unprocessed
    return jsonify(results=results, queue=process_queue)

@app.route('/api/bucket')
def bucket_operations():
    operation = request.args.get('operation')
    print operation
    if operation == 'fetch':
        filename = request.args.get('filename')
        result = aws.S3Action().streaming_download(filename)
    return send_file("/tmp/{filename}".format(filename=filename),
                     mimetype='text/json',
                     attachment_filename=filename,
                     as_attachment=True)

@app.route('/api/inventory')
def inventory():
    query = request.args.get('type')
    list = []
    if query == 'countbyregion':
        inventory = aws.Inventory()
        list = inventory.count_by_region()
        return 200
    if query == 'refresh':
        #inventory = aws.Inventory().refresh()
        asset = ir_assets.IR_Asset().refresh()
    return jsonify(results=list)

@app.route('/api/processes', methods=['GET', 'POST', 'DELETE'])
def processes():
    query = request.args.get('type')
    list = []
    assets = ir_assets.Asset_Processor()
    if query == 'unprocessed':
        list = assets.unprocessed_assets()
    if request.method == 'POST':
        assets.queue_asset(request.form["instance"])
    if request.method == 'DELETE':
        assets.dequeue_asset(request.form["instance"])

    return jsonify(results=list)

@app.route('/api/mitigation', methods=['GET', 'POST'])
def mitigation():
    list = []
    instance = request.args.get('instance')
    if instance is not None:
        instance_inventory = aws.Inventory().search(instance)
        ir_assets.Asset_Processor().process_asset(instance, instance_inventory)
    return jsonify(results=list)

@app.route('/api/memory/<lime_file>', methods=['GET'])
def memory_download(lime_file):
    action = request.args.get('action')
    list = []
    if action == 'volatility':
        if not aws.MemoryDumps.on_disk(lime_file):
            aws.S3Action().download_to_volatility(lime_file)
        else:
            pass
    return jsonify(results=list)

@app.route('/api/snapshot/<snapshot_id>', methods=['GET'])
def snapshot_process(snapshot_id):
    action = request.args.get('action')
    list = []
    if action == 'process':
        region = request.args.get('region')
        list = aws.Snapshot().launch_processor(snapshot_id, region)
    if action == 'timesketch':
        list = aws.Snapshot().timesketch(snapshot_id)
    return jsonify(results=list)
