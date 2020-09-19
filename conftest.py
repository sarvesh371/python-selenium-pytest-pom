__author__ = "sarvesh.singh"

from base.common import get_resource_config
import os
from collections import namedtuple
import pytest
from base.logger import Logger
from base.database import Database
from base.jenkins import JenkinsAutomation
from base.testrail_api import TestRailAPI
from base.slack_api import SlackNotification
from base.bitbucket import BitBucketApi
from base.web_drivers import WebDriver
from kafka import KafkaConsumer

logger = Logger(name="CONF_COMMON").get_logger


def pytest_addoption(parser):
    """
    Adds custom command line options for running the pytest harness
    All options will be stored in pytest config
    :param parser:
    :return:
    """
    parser.addoption("--url", action="store", default=None, help="URL")


def pytest_sessionstart(session):
    """
    Hook to be executed before session starts and before collection
    :param session:
    :return:
    """
    pass


def pytest_sessionfinish(session, exitstatus):
    """
    Hook to be executed after tests execution and session is about to end
    :param session:
    :param exitstatus:
    :return:
    """
    pass


def pytest_report_teststatus(report, config):
    """
    Hook for Test Status Report
    :param report:
    :param config:
    :return:
    """
    pass


def pytest_internalerror(excrepr, excinfo):
    """
    Hook if there is any internal error
    :param excrepr:
    :param excinfo:
    :return:
    """
    pass


def pytest_keyboard_interrupt(excinfo):
    """
    Hook Called when there is a Keyboard Interrupt
    :param excinfo:
    :return:
    """
    pass


def pytest_configure(config):
    """
    Configuration changes for PyTest
    :param config:
    :return:
    """
    logger.debug(f"Configure PyTest Options")
    os.environ["ROOT_PATH"] = config.rootdir.strpath
    config.option.cacheclear = True
    config.option.capture = "sys"  # no: for no output at all
    config.option.clean_alluredir = True
    config.option.color = "yes"
    config.option.disable_warnings = True
    config.option.instafail = True
    config.option.failedfirst = True
    config.option.json_report_indent = 2
    config.option.json_report_omit = ["warnings"]
    config.option.json_report = True
    config.option.maxfail = 1
    config.option.pythonwarnings = ["ignore:Unverified HTTPS request"]
    config.option.tbstyle = "short"
    config.option.self_contained_html = True
    config.option.verbose = 1

    if config.getoption("allure_report_dir") is None:
        config.option.allure_report_dir = f"allure-results"

    if config.getoption("json_report_file") == ".report.json":
        config.option.json_report_file = f"report.json"

    if config.getoption("htmlpath") is None:
        config.option.htmlpath = f"report.html"

    if config.getoption("xmlpath") is None:
        config.option.xmlpath = f"report.xml"


def pytest_runtest_setup(item):
    """
    Runs Before pytest_runtest_call
    :param item:
    """
    pass


def pytest_runtest_call(item):
    """
    Called to execute the Test item
    :param item:
    :param nextitem:
    """
    pass


def pytest_runtest_teardown(item, nextitem):
    """
    Runs after pytest_runtest_call
    :param item:
    :param nextitem:
    """
    pass


@pytest.hookimpl(trylast=True, hookwrapper=True)
def pytest_runtest_makereport():
    """
    This is a run into the report generated after a test case
    is done executing
    The hook here is used to add results to testrail/zephyr/reports after execution of a test case
    :param item:
    :param call:
    :return:
    """
    pass


@pytest.fixture(scope="session")
def db_connect():
    """
    Connect to Database
    :return:
    """
    logger.debug(f"Connecting to Database")
    host = None
    port = None
    user = None
    password = None

    details = f"{host} {port} {user} {password}"
    logger.debug(details)
    try:
        database = Database(
            host=host,
            username=user,
            password=password,
            database="postgres",
            port=port,
        )
    except Exception as exp:
        logger.error(exp)
        raise Exception(f"Unable to connect DB {details}")

    return database


@pytest.fixture(scope="session")
def jenkins():
    """
    Connect to Jenkins Fixture
    :return:
    """
    logger.debug(f"Connecting to Jenkins API Server")
    base_url = ''
    username = ''
    password = ''
    jenkins = JenkinsAutomation(
        base_url=base_url, username=username, password=password
    )

    return jenkins


@pytest.fixture(scope="session", autouse=True)
def resources():
    """
    resources Fixture with all Credentials and Url
    :return:
    """
    logger.debug(f"Reading Creds File")
    return get_resource_config()


@pytest.fixture(scope="session")
def test_rails(resources, request):
    """
    Get and fetch Test-Rail Creds
    :param resources:
    :param request:
    :return:
    """
    logger.debug(f"Connecting to Test-Rails API Server")
    if request.config.getoption("--test-rail"):
        data = resources.test_rails
        return TestRailAPI(
            url=data.url, email=data.email, password=data.api_key, exc=True, retry=10
        )
    else:
        return None


@pytest.fixture(scope="session")
def kafka():
    """
    Connect Kafka
    :return:
    :rtype:
    """
    consumer = KafkaConsumer('topicName', bootstrap_servers=['servers'])
    return consumer


@pytest.fixture(scope="session")
def slack_message(request):
    """
    Connect to Slack API
    :param request:
    :return:
    """
    logger.debug(f"Connecting to Slack API")
    return SlackNotification()


@pytest.fixture(scope="session")
def bit_bucket():
    """
    Fixture for Bitbucket Tokens
    :return:
    """
    logger.debug(f"Connecting to BitBucket API Server")
    return BitBucketApi()


@pytest.fixture(scope='session')
def web_driver():
    """
    Fixture to initialise the web driver
    :return:
    """
    driver = WebDriver(browser='chrome')
    yield driver
    try:
        driver.driver.close()
    except (Exception, ValueError):
        pass


@pytest.fixture(scope='session')
def page():
    """
    Fixture to initialise the Page Class
    :return:
    """
    named_tuple = namedtuple("page", ["page"])
    return named_tuple
