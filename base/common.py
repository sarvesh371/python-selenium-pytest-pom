__author__ = "sarvesh.singh"

from base.logger import Logger
import os
import logging
import sys
import pytest
from urllib.parse import urlsplit, urlparse, urlunparse
import re
from collections import namedtuple
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
from json import JSONDecodeError
from types import SimpleNamespace as Namespace
from datetime import datetime, date, timezone
import pytz
import allure
import uuid
from kafka import KafkaConsumer
import subprocess

logger = Logger(name="COMMON").get_logger


def basic_logging(name="BASIC", level=None):
    """
    Basic Logger to log in a file
    :param name
    :param level
    """
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")
    # coloredlogs.install()
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


def e2e_guid():
    """
    Function to generate GUID
    :return:
    """
    guid = str(uuid.uuid4())
    return f"e2e-{guid}"


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
