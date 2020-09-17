__author__ = "sarvesh.singh"

from base.logger import Logger
import os
import logging
import sys
import pytest
from urllib.parse import urlsplit, urlparse, urlunparse
import re
from collections import namedtuple
from functools import wraps
import time
import requests
from base.bitbucket import BitBucketApi
from base.database import Database
from base.jenkins import JenkinsAutomation
from testrail_api import TestRailAPI
from base.slack_api import SlackNotification
from base.web_drivers import WebDriver
from pathlib import Path
from json import (
    dumps as json_dumps,
    loads as json_loads,
    load as json_load,
    dump as json_dump,
)
from faker import Faker
from json import JSONDecodeError
from types import SimpleNamespace as Namespace
from datetime import datetime, date, timezone
import pytz
import allure
import uuid
from kafka import KafkaConsumer
import subprocess
import base64
import random
import string
from bs4 import BeautifulSoup
import zipfile
import secrets

logger = Logger(name="COMMON").get_logger


def basic_logging(name="BASIC", level=None):
    """
    Basic Logger to log in a file
    :param name
    :param level
    """
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")
    root = logging.getLogger(name=name)
    root.setLevel(getattr(logging, level))
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level))
    formatter = logging.Formatter("%(levelname)s :: %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)
    return root


def urljoin(*args):
    """
    This function will join a URL and return back proper url
    :return:
    """
    parsed = list(urlparse("/".join(args)))
    parsed[2] = re.sub("/{2,}", "/", parsed[2])
    _host = urlunparse(parsed)
    return _host


def read_json_file(file_name, nt=True):
    """
    This function will read Json and return it back in Named-Tuples format
    :param file_name
    :param nt
    """
    if not os.path.isfile(file_name):
        raise Exception(f"File {file_name} Does Not Exist !!")

    with open(file_name, "r") as _fp:
        if nt:
            data = json_load(_fp, object_hook=lambda d: Namespace(**d))
        else:
            data = json_load(_fp)

    return data


def get_resource_config():
    """
    Function to Read URL resource config File
    """
    data = Path(__file__).parent / "resources/config.json"
    return read_json_file(data, nt=True)


def process_response(response, report=True):
    """
    Function that will process response of a Rest Call
    :param response:
    :param report:
    :return:
    """
    # Saving all URL's that we are using in tests (for reference)
    global URLs
    URLs.add(response.request.url)
    with open("urlPaths.json", "w") as _fp:
        _fp.write(json_dumps(sorted(list(URLs)), indent=2, sort_keys=True))

    to_return = [
        "method",
        "url",
        "status_code",
        "reason",
        "headers",
        "content",
        "ok",
        "elapsed",
        "nt",
    ]
    RestResponse = namedtuple("RestResponse", to_return)

    headers = dict()
    for k, v in response.headers.items():
        headers[k] = v

    # Publish Rest Response Content
    try:
        content = response.content
        content = content.decode("utf-8")
    except UnicodeDecodeError:
        content = response.content
        content = content.decode("latin-1")

    try:
        content = json_loads(content)
    except JSONDecodeError:
        try:
            content = response.content.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            content = response.content

    if response.ok:
        if isinstance(content, dict):
            nt = json_loads(json_dumps(content), object_hook=lambda d: Namespace(**d))
        else:
            nt = None
    else:
        nt = None

    if content is None:
        raise Exception("ERROR Content is None !! Please Check")

    processed = RestResponse(
        method=response.request.method,
        url=response.request.url,
        status_code=response.status_code,
        reason=response.reason,
        headers=headers,
        content=content,
        ok=response.ok,
        elapsed=response.elapsed.microseconds,
        nt=nt,
    )
    os.environ["ELAPSED_TIME"] = str(response.elapsed.microseconds / 1000000)

    # Attach Response to allure in Json Format
    now = datetime.now(timezone("Asia/Calcutta"))
    if not response.ok:
        name = f"FailResponse_{now.minute}{now.second}{now.microsecond}"
    else:
        name = f"PassResponse_{now.minute}{now.second}{now.microsecond}"

    # Save only when it is process related response, else don't save it.
    if urlparse(response.request.url).hostname not in [
        "slack.com",
        "api.bitbucket.org",
    ]:
        if isinstance(content, dict) or isinstance(content, list):
            content = json_dumps(content, indent=2, sort_keys=True)
            allure.attach(
                content,
                name=f"{name}.json",
                attachment_type=allure.attachment_type.JSON,
            )
        elif isinstance(content, str):
            allure.attach(
                content, name=f"{name}.log", attachment_type=allure.attachment_type.TEXT
            )
        elif isinstance(content, bytes):
            allure.attach(
                content, name=f"{name}.jpg", attachment_type=allure.attachment_type.JPG
            )

    if not response.ok:
        # Not sending Header in Error Response
        if report:
            logger.error(processed)
        raise Exception(
            json_dumps(
                processed, default=lambda o: o.__dict__, indent=2, sort_keys=True
            )
        )

    if urlparse(response.request.url).hostname in [
        "slack.com",
    ]:
        return processed

    return processed

    if not os.path.isdir("test_data/verification_data/dumps"):
        os.makedirs("test_data/verification_data/dumps")

    # TODO Dumping the Response in a file for further use
    file_name = urlparse(response.request.url).path
    matcher = re.search(r"(.*?)\?", file_name, re.I | re.M)
    if matcher:
        file_name = matcher.group(1)
    matcher = re.search(r"(.*?)::", file_name, re.I | re.M)
    if matcher:
        file_name = matcher.group(1)
    if file_name.split("/")[-1] not in ["info", "version", "token"] and isinstance(
            processed.content, dict
    ):
        file_name = str("_".join(file_name.split("/")[1::])).replace("-", "_")
        _keys = sorted(list(set(get_all_keys_in_dict(processed.content))))
        with open(f"test_data/verification_data/dumps/{file_name}.json", "w") as _fp:
            _fp.write(json_dumps(_keys, indent=2, sort_keys=True))


def generate_curl_command(method, headers, url, params=None, data=None):
    """
    Get Curl Command Before it is being Hit !!
    :param method:
    :param headers:
    :param url:
    :param params:
    :param data:
    :return:
    """
    # Check if data is in Json/dict format, convert it into string after that
    if isinstance(data, dict) or isinstance(data, list):
        data = json_dumps(data)
    headers = " -H ".join(
        [
            f'"{k}: {v}"'
            for k, v in headers.items()
            if k not in ["User-Agent", "Accept-Encoding"]
        ]
    )

    if params:
        url = f'{url}?{"&".join([f"{k}={v}" for k, v in params.items()])}'

    if data:
        command = f"curl -i -sS -X {method} -H {headers} -d '{data}' '{url}'"
    else:
        command = f"curl -i -sS -X {method} -H {headers} '{url}'"

    now = datetime.now(pytz.timezone("Asia/Calcutta"))
    name = f"CurlCmd_{now.minute}{now.second}{now.microsecond}.json"
    if urlparse(url).hostname not in ["slack.com", "testrail.io", "api.bitbucket.org"]:
        allure.attach(command, name=name, attachment_type=allure.attachment_type.TEXT)

    global curlCmds
    curlCmds.append(command)
    with open("curlCommands.json", "w") as _fp:
        _fp.write(json_dumps(curlCmds, indent=2, sort_keys=True))

    # We always save Curl Command in environment variable, so that we know (in-case) of an exception what was it.
    os.environ["CURL"] = command
    return command


def run_cmd(cmd, wait=True):
    """
    Run an external command, wait and display it's output and return back it's output as well
    :param cmd:
    :param wait:
    :return:
    """
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    CmdResponse = namedtuple("RestResponse", ["cmd", "status", "output", "error"])

    if wait:
        (output, err) = p.communicate()
        status = p.wait()
        return CmdResponse(cmd=cmd, status=status, output=output.decode(), error=err.decode())
    else:
        return


def get_adb_device():
    devices = str(run_cmd("adb devices").output).strip()
    return re.findall(r"^(.*?)\s+device$", devices, re.I | re.M)


def base64_encode(username, password):
    """
    Return Base64 encoded string
    :param username:
    :param password:
    :return:
    """
    encoded = str(base64.b64encode(bytes(f"{username}:{password}", "utf-8")), "ascii").strip()
    return encoded


def base64_decode(data):
    """
    Return Base64 encoded string
    :return:
    """
    decoded = str(base64.b64decode(data), "ascii")
    if len(decoded.split(":")) != 2:
        raise Exception("This is not a valid username password encoded string !!")
    username = decoded.split(":")[0]
    password = decoded.split(":")[1]
    return username, password


def generate_random_alpha_numeric_string(length=10):
    """
    Function to generate Random Alpha Numeric String
    :param length:
    :return:
    """
    random_alpha_numeric_string = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(length)
    )
    return random_alpha_numeric_string


def generate_random_string(length=10):
    """
    Function to generate Random String
    :param length:
    :return:
    """
    random_string = "".join(
        random.choice(string.ascii_uppercase) for _ in range(length)
    )
    return random_string


def generate_guid():
    """
    Function to generate GUID
    :return:
    """
    guid = str(uuid.uuid4())
    return guid


def generate_random_password(length=10):
    """
    Generate a Random Password of length characters
    :param length:
    :return:
    """
    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def generate_random_number(low=0, high=99, include_all=False):
    """
    Function to generate a Random Number between low and high range
    :param low: Lowest Random Number
    :param high: Highest Random Number
    :param include_all: Highest Random Number
    :return: A Random number between Low and High
    """
    if include_all:
        number = random.randint(low, high)
    else:
        number = random.randrange(low, high)
    return number


def generate_birth_date(member="adult"):
    """
    Function to generate Birth Date
    :param member:
    :return:
    """
    minor_range = list(range(1, 5))  # 1 to 5 years of minor
    child_range = list(range(5, 10))  # 5 to 10 years of children
    adult_range = list(range(22, 59))  # 22 years to 59 years of adults
    year_today = int(datetime.now().year)

    if member == "child":
        start = year_today - child_range[-1]
        end = year_today - child_range[0]
    elif member == "minor":
        start = year_today - minor_range[-1]
        end = year_today - minor_range[0]
    else:
        start = year_today - adult_range[-1]
        end = year_today - adult_range[0]

    return date(
        random.randint(start, end), random.randint(1, 12), random.randint(1, 28)
    )


def generate_phone_number(max_digits=10):
    """
    Function to generate phone number
    :param max_digits:
    :return:
    """
    return random.randint(10 ** (max_digits - 1), 10 ** max_digits - 1)


def generate_first_name(from_saved=False):
    """
    Function to generate First Name
    :return:
    """
    saved_ids = [
        "Carol",
        "Caroline",
        "Carolyn",
        "Deirdre",
        "Chloe",
        "Claire",
        "Deirdre",
        "Diana",
        "Donna",
        "Dorothy",
        "Elizabeth",
        "Zoe",
        "Wendy",
        "Wanda",
        "Virginia",
        "Victoria",
        "Vanessa",
        "Una",
        "Tracey",
        "Theresa",
        "Sue",
        "Stephanie",
        "Sophie",
        "Sonia",
        "Sarah",
        "Samantha",
        "Sally",
        "Ruth",
    ]
    if from_saved:
        return random.choice(saved_ids)
    else:
        return str(Faker().first_name())


def generate_last_name(from_saved=False):
    """
    Function to generate Last Name
    :return:
    """
    saved_ids = [
        "Simon",
        "Stephen",
        "Steven",
        "Stewart",
        "Thomas",
        "Tim",
        "Trevor",
        "Victor",
        "Warren",
        "William",
        "Alan",
        "Elliott",
        "Victor",
        "Bryce",
        "Finn",
        "Brantley",
        "Edward",
        "Abraham",
        "Sebastian",
        "Sean",
        "Sam",
        "Robert",
        "Richard",
        "Piers",
        "Phil",
        "Peter",
        "Paul",
        "Owen",
    ]
    if from_saved:
        return random.choice(saved_ids)
    else:
        return str(Faker().last_name())


def dict_to_ns(dictionary):
    """
    Convert Dictionary to Name-Spaced Items
    :param dictionary:
    :return:
    """
    return json_loads(json_dumps(dictionary), object_hook=lambda d: Namespace(**d))


def parse_html(content):
    soup = BeautifulSoup(content, features="lxml")
    return soup


def compress_file(file_name):
    """
    Compress a file and return it's path
    :param file_name
    """
    if str(file_name).endswith("zip"):
        return file_name
    else:
        zip_name = ".".join([*[x for x in file_name.split(".")[0:-1]], *["zip"]])

    _zip = zipfile.ZipFile(zip_name, "w")
    _zip.write(file_name, compress_type=zipfile.ZIP_DEFLATED)
    _zip.close()

    return zip_name


def is_key_there_in_dict(key, dictionary, empty_check=True, text=None):
    """
    Check if key is there in dictionary
    :param key:
    :param dictionary:
    :param empty_check:
    :param text:
    :return:
    """
    if key not in dictionary:
        if text is None:
            logger.error(f"'{key}' not found in _content !!")
            raise Exception(f"'{key}' not found in _content !!")
        else:
            logger.error(f"'{key}' not found in _content | {text}")
            raise Exception(f"'{key}' not found in _content | {text}")
    else:
        if empty_check:
            if isinstance(dictionary[key], (list, tuple, dict)):
                if len(dictionary[key]) == 0:
                    logger.debug(f"{key} is empty !!")
            elif dictionary[key] is None:
                pass
            else:
                pass


def retry(retries=10, interval=4):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = retries
            final_exception = None
            while r > 0:
                try:
                    response = func(*args, **kwargs)
                except Exception as exp:
                    r -= 1
                    logger.info(f"{exp} :: {r} of {retries} Retries Left !!")
                    time.sleep(interval)
                    final_exception = exp
                    pass
                else:
                    break
            else:
                logger.error(final_exception)
                raise Exception(f"{retries} Retries Exhausted :: {final_exception} !!")
            return response

        return wrapper

    return deco


def send_post_request(url, data, headers, params=None):
    """
    Send simple Post Request
    :param url:
    :param data:
    :param headers:
    :param params:
    :return:
    """
    response = requests.request(
        "POST", url, data=data, headers=headers, params=params, verify=False
    )
    return process_response(response)


def send_get_request(url, headers=None, params=None, timeout=None, report=True):
    """
    Send simple Post Request
    :param url:
    :param headers:
    :param params:
    :param timeout:
    :param report:
    :return:
    """
    if timeout:
        response = requests.request(
            "GET", url, headers=headers, params=params, timeout=timeout, verify=False
        )
    else:
        response = requests.request(
            "GET", url, headers=headers, params=params, verify=False
        )

    return process_response(response, report)


def generate_test_plan(test_rails, cases):
    """
    Generate Test Plan in Test Rails
    :param test_rails
    :param cases
    """
    milestone = 50
    configuration = 50
    logger.debug(
        f"Creating Test Plan: MileStone: {milestone} and Configuration: {configuration}"
    )
    data = None
    # Generate a Test-Plan, retry till it is created. this is to handle 409 error sent by test-rails when it is in
    # maintenance mode. So, there is no choice with this as the window can be as long as 30 minutes
    created = False
    while not created:
        try:
            plan_data = []
            for suit in test_rails.suites.get_suites(project_id=1):
                suite_id = suit["id"]
                case_ids = test_rails.cases.get_cases(project_id=1, suite_id=suite_id)
                case_ids = [x["id"] for x in case_ids if x["id"] in cases]
                cases = list(set(cases) - set(case_ids))
                if len(case_ids) == 0:
                    continue
                plan_data.append({
                    "suite_id": suite_id,
                    "include_all": False,
                    "case_ids": case_ids,
                    "config_ids": [configuration],
                    "runs": [{
                        "include_all": False,
                        "case_ids": case_ids,
                        "config_ids": [configuration],
                    }],
                })

            # Raise Exception if all test-cases are not consumed
            if len(cases) > 0:
                raise Exception(f"Test-Cases {cases} are Orphans !! Please check in test-suits")

            # Generate a test plan with data now
            plan_id = test_rails.plans.add_plan(
                project_id=1,
                name='Test',
                description='Test',
                milestone_id=milestone,
                entries=plan_data,
            )
            created = True

            # Get Test-Cases against run-id for results submission
            for count, _data in enumerate(plan_data):
                suite_id = _data["suite_id"]
                for entry in plan_id["entries"]:
                    if suite_id == entry["suite_id"]:
                        plan_data[count]["runs"][0].update(entry["runs"][0])
                        break

            logger.debug(f"Test Plan: {plan_id['id']}")
            data = {"test_plan": plan_id["url"], "testRailData": plan_data, "plan_id": plan_id["id"]}
        except (Exception, ValueError) as exp:
            logger.error(f"Retrying as Test Plan Creation Failed with error {exp} ")
            time.sleep(10)

    return data


def uncurl_from_curl(command):
    """
    Uncurl the curl command and return args for request command
    """
    url = None
    if re.search(r"--request", command):
        url = str(command.split(" ")[4]).replace("'", "")
        method = str(re.search(r"--request\s+(.*?)\s+", command, re.I | re.M).group(1)).upper()
        if re.search(r"--data-raw\s*'([^']*)'", command) is not None:
            data = json_loads(re.search(r"--data-raw\s*'([^']*)'", command, re.I | re.M).group(1))
        else:
            data = None
        headers = {
            str(x.split(":")[0]).strip(): str(x.split(":")[1]).strip()
            for x in re.findall(r"--header \'(.*?)\'", command, re.I | re.M)
        }
    else:
        url = re.search(r"'(http.*?)'$", command, re.I | re.M).group(1)
        method = str(re.search(r"-x\s+(.*?)\s+", command, re.I | re.M).group(1)).upper()
        if re.search(r"-d\s*'(.*?)'", command) is not None:
            data = json_loads(re.search(r"-d\s*'(.*?)'", command, re.I | re.M).group(1))
        else:
            data = None
        headers = {
            str(x.split(":")[0]).strip(): str(x.split(":")[1]).strip()
            for x in re.findall(r"-H \"(.*?)\"", command, re.I | re.M)
        }
    return {"method": method, "url": url, "data": data, "headers": headers}


def create_auth_basic_token(login, secret):
    """
    Function to create basic token from id and secret
    :param login:
    :param secret:
    """
    login = str(base64.b64decode(login), "ascii").strip()
    secret = str(base64.b64decode(secret), "ascii").strip()
    token = str(
        base64.b64encode(bytes("%s:%s" % (login, secret), "utf-8")), "ascii"
    ).strip()
    return token


def save_allure(data, name, save_dump=True):
    """
    Save allure report by converting data to Json
    :param data:
    :param name:
    :param save_dump:
    :type name:
    :return:
    """
    if len(data) != 0:
        if isinstance(data, str):
            name = str(name).replace(".json", ".log")
            allure.attach(data, name=name, attachment_type=allure.attachment_type.TEXT)
            if save_dump:
                with open(name, "w") as _fp:
                    _fp.write(data)
            return str
        else:
            dump = json_dumps(data, indent=2, sort_keys=True)
            allure.attach(dump, name=name, attachment_type=allure.attachment_type.JSON)
            if save_dump:
                with open(name, "w") as _fp:
                    _fp.write(dump)
            return dump


def save_json(data, name):
    """
    Save Json
    :param data:
    :param name:
    :return:
    """
    with open(name, 'w') as _fp:
        _fp.write(json_dumps(data, indent=2, sort_keys=True))


def save_csv(data, name):
    """
    Save CSV
    :param data:
    :param name:
    :return:
    """
    with open(name, 'w') as _fp:
        _fp.write("\n".join(data))
