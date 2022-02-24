import logging
import os
import sys
from os import path
from urllib.parse import urljoin

import requests
import yaml
import time
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    encoding='utf-8',
    level=logging.DEBUG,
    stream=sys.stdout
)

BASE_URL = os.getenv("QUEUE_MGR_URL")
if BASE_URL is None:
    logging.error("QUEUE_MGR_URL is not set.")
    quit(1)
logging.info("BASE_URL = %s", BASE_URL)

DATA_DIRECTORY = os.getenv("DATA_DIRECTORY")
if DATA_DIRECTORY is None:
    logging.error("DATA_DIRECTORY is not set.")
    quit(1)
logging.info("DATA_DIRECTORY = %s", DATA_DIRECTORY)

QUEUE_MGR_NAME = os.getenv("QUEUE_MGR_NAME")
if QUEUE_MGR_NAME is None:
    logging.error("QUEUE_MGR_NAME is not set.")
    quit(1)
logging.info("QUEUE_MGR_NAME = %s", QUEUE_MGR_NAME)

USERNAME = os.getenv("USERNAME")
if USERNAME is None:
    logging.error("USERNAME is not set.")
    quit(1)
logging.info("USERNAME = %s", USERNAME)

PASSWORD = os.getenv("PASSWORD")
if PASSWORD is None:
    logging.error("PASSWORD is not set.")
    quit(1)

basicCredentials = HTTPBasicAuth(USERNAME, PASSWORD)

QUEUE_URL = "/ibmmq/rest/v1/admin/qmgr/{queueManager}/queue"
TOPIC_URL = "/ibmmq/rest/v1/admin/qmgr/{queueManager}/topic"
MQSC_URL = "/ibmmq/rest/v2/admin/action/qmgr/{queueManager}/mqsc"

QUEUE_MGR_URL = "ibmmq/rest/v2/admin/qmgr"

url = urljoin(BASE_URL, QUEUE_MGR_URL)

queues_path = path.join(DATA_DIRECTORY, "queues.yml")
topics_path = path.join(DATA_DIRECTORY, "topics.yml")
subscriptions_path = path.join(DATA_DIRECTORY, "subscriptions.yml")
permissions_path = path.join(DATA_DIRECTORY, "permissions.yml")


def run_command_json(command, qualifier=None, name=None, parameters=None):
    headers = {
        "Content-Type": "application/json",
        "ibm-mq-rest-csrf-token": "really?"
    }
    payload = {
        "type": "runCommandJSON",
        "command": command,
    }
    if qualifier:
        payload["qualifier"] = qualifier
    if parameters:
        payload["parameters"] = parameters
    if name:
        payload["name"] = name

    mqsc_url = urljoin(BASE_URL, MQSC_URL.format(queueManager=QUEUE_MGR_NAME))
    logging.debug("Calling runCommandJSON on %s with:\n%s", mqsc_url, payload)
    r = requests.post(mqsc_url, json=payload, verify=False, auth=basicCredentials, headers=headers)
    logging.debug("Response from runCommandJSON on %s status %s:\n%s", mqsc_url, r.status_code,
                  r.text)


def apply_data(type, data_path):
    if path.exists(data_path):
        logging.info("Loading %s data from %s", type, data_path)
        with open(data_path, 'r') as file:
            data = yaml.safe_load(file)
            logging.debug("%s data loaded:\n%s", type, data)

        for name, parameters in data.items():
            logging.info("Processing %s: %s", type, name)
            run_command_json("define", type, name, parameters)
    else:
        logging.warning("%s data was not found %s", type, data_path)


def apply_permissions(data_path):
    if path.exists(data_path):
        with open(data_path, 'r') as file:
            data = yaml.safe_load(file)
            logging.debug("%s data loaded:\n%s", "permission", data)

            for name, parameters in data.items():
                parameters["profile"] = name
                run_command_json("set", "authrec", None, parameters)
    else:
        logging.warning("%s data was not found %s", "permission", data_path)


MAX_ATTEMPTS = 30
count = 0
while count < MAX_ATTEMPTS:
    count += 1
    try:
        run_command_json("ping", "QMGR")
    except:
        logging.warning("Exception thrown pinging queue manager. Attempt %s of %s.", count, MAX_ATTEMPTS)
        if count < MAX_ATTEMPTS:
            time.sleep(10)
        else:
            logging.error("Too many exceptions trying to ping queue manager")
            quit(1)

apply_data("qlocal", queues_path)
apply_data("topic", topics_path)
apply_data("sub", subscriptions_path)
apply_permissions(permissions_path)