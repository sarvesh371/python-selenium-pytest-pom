__author__ = "sarvesh.singh"

from base.common import (
    base64,
    urljoin,
)
from base.rest import SendRestRequest
from base.logger import Logger
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = Logger(name="JENKINS").get_logger


class JenkinsAutomation(SendRestRequest):
    """
    Class to perform all Jenkins automation
    """

    JOB_DETAILS = "{}/job/{}/api/json?tree=allBuilds[*]&depth=2"
    DELETE_URL = "{}/job/{}/{}/doDelete"
    CONSOLE_LOGS_URL = "{}/job/{}/{}/consoleText"
    REBUILD_JOB_URL = "{}/job/{}/{}/rebuild/configSubmit"
    BUILD_WITH_PARAMS_URL = "{}/job/{}/buildWithParameters"
    BUILD_DETAILS = "{}/job/{}/{}/api/json"
    LAST_BUILD = "{}/job/{}/lastBuild/api/json"
    LAST_SUCCESS_BUILD = "{}/job/{}/lastSuccessfulBuild/api/json"
    QUEUE_ITEM = "{}/queue/item/{}/api/json"
    WF_API_RUNS = "{}/job/{}/wfapi/runs"
    WF_API = "{}/job/{}/{}/wfapi"
    ARTIFACTS = "{}/job/{}/{}/api/json?tree=artifacts[*]"
    KILL_ALL = "{}/job/{}/{}/kill"

    def __init__(self, base_url, username, password):
        """
        Init Class to interact with Jenkins
        :param base_url:
        :param username:
        :param password:
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        super().__init__()

        auth = str(
            base64.b64encode(
                bytes("{}:{}".format(self.username, self.password), "utf-8")
            ),
            "ascii",
        ).strip()
        self.session.headers.update({"Authorization": "Basic {}".format(auth)})
        self.session.verify = False

    def delete_build(self, name, number):
        """
        Function to delete build
        :param name:
        :param number:
        :return:
        """
        url = self.DELETE_URL.format(self.base_url, name, number)
        self.send_request("POST", url=url)
        logger.info(f"Build # {number} of {name} Deleted !!")

    def get_all_jobs(self, name):
        """
        Get all Jobs for a build
        :param name:
        :return:
        """
        url = self.JOB_DETAILS.format(self.base_url, name)
        _content = self.send_request("GET", url=url).content
        return _content["allBuilds"]

    def get_failed_builds(self, name):
        """
        Get last failed builds
        :param name:
        :return:
        """
        url = self.JOB_DETAILS.format(self.base_url, name)
        _content = self.send_request("GET", url=url).content
        for build in _content["allBuilds"]:
            url = f"{build['url']}api/json"
            build_response = self.send_request("GET", url=url).content
            result = build_response["result"]
            number = build_response["number"]
            if result == "SUCCESS":
                self.delete_build(name, number)
            else:
                self.get_console_logs(name, number)

    def get_console_logs(self, name, number):
        """
        Function to Get Console Logs of a build
        :param name:
        :param number:
        :return:
        """
        url = self.CONSOLE_LOGS_URL.format(self.base_url, name, number)
        _content = self.send_request("GET", url=url).content
        return _content

    def get_user_name(self, name, number):
        """
        Get User Name who triggered the Job from displayName
        :param name:
        :param number:
        :return:
        """
        users = []
        url = self.BUILD_DETAILS.format(self.base_url, name, number)
        _content = self.send_request("GET", url=url).content
        users.append(str(_content["displayName"]).split(" ")[-1])
        for _action in _content["actions"]:
            if "_class" in _action and _action["_class"] == "hudson.model.CauseAction":
                if "causes" in _action:
                    for _cause in _action["causes"]:
                        if _cause["_class"] == "hudson.model.Cause$UserIdCause":
                            users.append(_cause["userId"])
                            break
        _final_list = []
        for _user in users:
            if "@" not in _user:
                _final_list.append(f"{str(_user).lower()}@test.com")
            else:
                _final_list.append(str(_user).lower())

        return _final_list

    def get_build_params(self, name, number):
        """
        Get Build Parameters
        :param name:
        :param number:
        :return:
        """
        url = self.BUILD_DETAILS.format(self.base_url, name, number)
        _content = self.send_request("GET", url=url).content
        for action in _content["actions"]:
            if "_class" in action:
                if action["_class"] == "hudson.model.ParametersAction":
                    return {x["name"]: x["value"] for x in action["parameters"]}

    def rebuild_job(self, name, number):
        """
        Rebuild a Job
        :param name:
        :param number:
        :return:
        """
        params = self.get_build_params(name, number)
        url = self.BUILD_WITH_PARAMS_URL.format(self.base_url, name)
        response = self.send_request("POST", url=url, params=params)
        queue = int(response.headers["Location"].split("/")[-2])
        url = self.QUEUE_ITEM.format(self.base_url, queue)
        while True:
            _content = self.send_request("GET", url=url).content
            if "executable" in _content:
                return _content["executable"]
            else:
                time.sleep(1)

    def get_last_build(self, name):
        """
        Get Last Build that has been triggered
        :param name:
        :return:
        """
        # Fetch the latest build ID after re-running
        url = self.LAST_BUILD.format(self.base_url, name)
        _content = self.send_request("GET", url=url).content
        return _content

    def get_last_successful_build(self, name):
        """
        Get Last Successful Build that has been triggered
        :param name:
        :return:
        """
        # Fetch the latest build ID after re-running
        url = self.LAST_SUCCESS_BUILD.format(self.base_url, name)
        _content = self.send_request("GET", url=url).content
        return _content

    def delete_successful_jobs(self, name):
        """
        This function will delete all successful Jobs
        Which may end up cluttering complete Jenkins
        :param name:
        :return:
        """
        two_days_before = datetime.now().timestamp() - 3600 * 24 * 2
        url = self.JOB_DETAILS.format(self.base_url, name)
        _content = self.send_request("GET", url=url).content
        for build in _content["allBuilds"]:
            timestamp = int(build["timestamp"] / 1000)
            result = build["result"]
            number = build["number"]
            if result == "SUCCESS" or timestamp <= two_days_before:
                self.delete_build(name, number)

    def get_last_success_build_artifact_links(self, name, file_type=".json"):
        """
        Function to Get Links of artifacts of last successful build
        :param name:
        :param file_type:
        :return:
        """
        _build = self.get_last_successful_build(name)
        _artifact_links = dict()
        for artifact in _build["artifacts"]:
            _url = f"{_build['url']}artifact/{artifact['relativePath']}"
            if str(artifact["relativePath"]).endswith(file_type):
                _artifact_links[artifact["relativePath"]] = _url
        return _artifact_links

    def get_artifact_data_from_jenkins(self, url):
        """
        Function to get artifact data from Jenkins
        :param url:
        :return:
        """
        _content = self.send_request("GET", url=url).content
        if isinstance(_content, list):
            return _content
        elif isinstance(_content, str):
            return _content
        else:
            return dict(_content)

    @staticmethod
    def filter_data_based_on_description(filtered_data):
        """
        Filter Data based on Description
        :param filtered_data:
        :return:
        """
        final_data = []
        descriptions = {x["description"] for x in filtered_data}
        for description in descriptions:
            for data in filtered_data:
                if data["description"] == description and data["status"] != "IN_PROGRESS":
                    final_data.append(data)
                    break
        return final_data

    def wait_for_stage(self, name, number, stages_to_wait, timeout=600):
        """
        Function to wait for a stage to come in a Build
        :param name:
        :param number:
        :param stages_to_wait:
        :param timeout:
        :return:
        """
        now = int(time.time())
        while int(time.time()) - now < timeout:
            logger.info(f"Waiting for {name} {number} to Complete Stage ...")
            _content = self.send_request(
                "GET", url=self.WF_API.format(self.base_url, name, number)
            ).content
            stages = {x["name"]: x["status"] for x in _content["stages"]}
            if _content["status"] == "IN_PROGRESS":
                for _stage in stages_to_wait:
                    if _stage in stages and stages[_stage] != "IN_PROGRESS":
                        logger.info(
                            f"Build # {number} is in {_stage} Stage, Triggering Next Job (if there) ..."
                        )
                        return
                else:
                    logger.debug("Waiting for 15 seconds to check next status")
                    time.sleep(15)
            elif _content["status"] == "SUCCESS":
                return
            else:
                time.sleep(60)

    def get_artifacts(self, name, number):
        """
        Get Artifacts from name and number for a job, returns only list of URL's
        :param name:
        :param number:
        :return:
        """
        url = self.ARTIFACTS.format(self.base_url, name, number)
        response = self.send_request("GET", url=url).content["artifacts"]
        url = urljoin(self.base_url, "job", str(name), str(number), "artifact")
        return [urljoin(url, x["relativePath"]) for x in response]

    def get_all_build_details(self, name, ignore_failed=True):
        """
        Get All Build details, which also include params and artifacts
        :param name:
        :param ignore_failed:
        :return:
        """
        jobs = self.get_all_jobs(name)
        if ignore_failed:
            jobs = [x for x in jobs if x["result"] == "SUCCESS"]

        def worker_func(number):
            params, artifacts = (None, None)
            try:
                params = self.get_build_params(name, number)
                artifacts = self.get_artifacts(name, number)
            except (Exception, ValueError):
                pass

            return params, artifacts

        with ThreadPoolExecutor(max_workers=50) as executor:
            thread_executor = {
                executor.submit(worker_func, job["number"]): (count, job) for count, job in enumerate(jobs)
            }
            for completed_thread in as_completed(thread_executor):
                count, job = thread_executor[completed_thread]
                if completed_thread.exception():
                    continue
                jobs[count]['params'], jobs[count]['artifacts'] = completed_thread.result()

        return [x for x in jobs if x["artifacts"] is not None and x["params"] is not None]

    def kill_all_jobs(self, name):
        """
        Kill all Building Jobs
        :param name:
        :return:
        """
        jobs = self.get_all_jobs(name)
        building = [x for x in jobs if x["building"] is True]
        for _now in building:
            url = self.KILL_ALL.format(self.base_url, name, _now["number"])
            print(f"Killing {name} #{_now['number']}")
            response = self.send_request("POST", url=url)
            if response.ok is not True:
                print(f"Killing {name} #{_now['number']} Failed !!")

    def build_job(self, url, params):
        """
        Build a Job
        :param url:
        :param params:
        :return:
        """
        response = self.send_request("POST", url=url, params=params)
        queue = int(response.headers["Location"].split("/")[-2])
        return queue

    def get_built_job_details(self, queue):
        """
        Ge build details
        :param queue:
        :return:
        """
        url = self.QUEUE_ITEM.format(self.base_url, queue)
        while True:
            _content = self.send_request("GET", url=url).content
            if "executable" in _content:
                return _content["executable"]
            else:
                time.sleep(1)
