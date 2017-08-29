#!/usr/bin/env python

from flask import Flask
from flask import request
from flask import abort
import pytz
import json
import logging
import binascii
import dateutil.parser
import hmac
from hashlib import sha1
from datetime import datetime
from infoblox_client import connector
from infoblox_client import objects


config_file = './config_prod.json'

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

# will be overridden if present in config_file
SCALR_SIGNING_KEY = ''
INFOBLOX_HOST = ''
INFOBLOX_USERNAME = ''
INFOBLOX_PASSWORD = ''


@app.route("/infoblox/", methods=['POST'])
def webhook_listener():
    if not validate_request(request):
        abort(403)

    data = json.loads(request.data)
    if 'eventName' not in data or 'data' not in data:
        abort(404)

    if data['eventName'] == 'HostUp':
        return add_server(data['data'])
    elif data['eventName'] in ['HostDown', 'BeforeHostTerminate']:
        return delete_server(data['data'])


def get_hostname(data):
    hostname = data['SCALR_EVENT_SERVER_HOSTNAME'].split(".")[0]
    domain = data['DOMAIN']
    fqdn = hostname.lower() + "." + domain
    return fqdn


def get_ip(data):
    if data['SCALR_EVENT_INTERNAL_IP']:
        return data['SCALR_EVENT_INTERNAL_IP']
    else:
        return data['SCALR_EVENT_EXTERNAL_IP']


def add_server(data):
    conn = connector.Connector({'host': INFOBLOX_HOST, 'username': INFOBLOX_USERNAME, 'password': INFOBLOX_PASSWORD})
    hostname = get_hostname(data)
    ip = get_ip(data)
    logging.info('Registering %s : %s', hostname, ip)
    my_ip = objects.IP.create(ip=ip)
    host = objects.HostRecord.create(conn, name=hostname, ip=my_ip)
    # additional fields in host record?
    # additional DNS records? CNAMES?
    return 'Ok {}'.format(host)


def delete_server(data):
    conn = connector.Connector({'host': INFOBLOX_HOST, 'username': INFOBLOX_USERNAME, 'password': INFOBLOX_PASSWORD})
    hostname = get_hostname(data)
    ip = get_ip(data)
    logging.info('Deregistering %s : %s', hostname, ip)
    my_ip = objects.IP.create(ip=ip)
    hr = objects.HostRecord.search(conn, name=hostname, ip=my_ip)
    if not hr:
        logging.warning('Host Record not found, nothing to delete.')
        return 'Not changed'
    hr.delete()
    return 'Deletion ok'


def validate_request(request):
    if 'X-Signature' not in request.headers or 'Date' not in request.headers:
        return False
    date = request.headers['Date']
    body = request.data
    expected_signature = binascii.hexlify(hmac.new(SCALR_SIGNING_KEY, body + date, sha1).digest())
    if expected_signature != request.headers['X-Signature']:
        return False
    date = dateutil.parser.parse(date)
    now = datetime.now(pytz.utc)
    delta = abs((now - date).total_seconds())
    return delta < 300


def load_config(filename):
    with open(filename) as f:
        options = json.loads(f.read())
        for key in options:
            if key in ['INFOBLOX_HOST', 'INFOBLOX_USERNAME', 'INFOBLOX_PASSWORD']:
                logging.info('Loaded config: {}'.format(key))
                globals()[key] = options[key]
            elif key in ['SCALR_SIGNING_KEY']:
                logging.info('Loaded config: {}'.format(key))
                globals()[key] = options[key].encode('ascii')


load_config(config_file)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
