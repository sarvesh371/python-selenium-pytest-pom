__author__ = "sarvesh.singh"

import os
import logging
import sys
from urllib.parse import urlparse, urlunparse
import re
import subprocess
from collections import namedtuple
from pathlib import Path
from json import (
    dumps as json_dumps,
    loads as json_loads,
    load as json_load,
)
from types import SimpleNamespace as Namespace
import allure
import logging.handlers


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
    data = Path(__file__).parent.parent / "resources/config.json"
    return read_json_file(data, nt=True)


def dict_to_ns(dictionary):
    """
    Convert Dictionary to Name-Spaced Items
    :param dictionary:
    :return:
    """
    return json_loads(json_dumps(dictionary), object_hook=lambda d: Namespace(**d))


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
