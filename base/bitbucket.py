__author__ = "sarvesh.singh"

from base.common import (
    urljoin,
    get_resource_config,
    basic_logging,
    dict_to_ns,
)
from base.logger import Logger
from time import sleep
from urllib.parse import urlparse
import re
from requests import session


class BitBucketApi:
    def __init__(self):
        """
        Bit Bucket API to interact with Bit bucket
        """
        self.base = "https://api.bitbucket.org/2.0/"
        self.resource = get_resource_config()
        self.session = session()
        self.logger = Logger(name="BitBucket").get_logger
        self.logger = basic_logging("BitBucket")
        self.session.auth = (self.resource.bit_bucket.username, self.resource.bit_bucket.password)

    def send_request(self, **kwargs):
        """
        Send a Request on Remote Server
        :param kwargs:
        :return:
        """
        response = self.session.request(**kwargs)
        try:
            response.raise_for_status()
        except (Exception, ValueError) as exp:
            if response.status_code == 429:
                self.logger.error(f"Bit Bucket Rate Limit Reached, Waiting to re-try")
                while response.status_code == 429:
                    response = self.session.request(**kwargs)
                    sleep(10)
            else:
                if hasattr(exp.response, "reason"):
                    self.logger.error(
                        f"{exp.response.reason} With Code: {response.status_code} while processing {kwargs}")
                else:
                    self.logger.error(f"Got Error Code: {response.status_code} while processing {kwargs}")
                raise Exception(exp)

        return self.process_response(response, kwargs)

    def process_response(self, response, kwargs):
        """
        Process the received Response
        :param response:
        :param kwargs:
        :return:
        """
        if 'application/json' not in response.headers.get('content-type'):
            return response.text

        if 'values' in response.json():
            data = response.json()['values']
        else:
            data = response.json()

        if 'params' in kwargs and 'page' in kwargs['params'] and 'next' in response.json():
            parsed = urlparse(response.json()['next'])
            params = {x.split('=')[0]: x.split('=')[1] for x in parsed.query.split('&')}
            if 'page' in params and len(params['page']) == len(re.sub('\D', '', params['page'])) and int(
                    params['page']) - 1 == int(kwargs['params']['page']):
                return data
        if 'next' in response.json():
            parsed = urlparse(response.json()['next'])
            kwargs['url'] = urljoin(f"{parsed.scheme}://{parsed.hostname}", parsed.path)
            kwargs['params'] = {x.split('=')[0]: x.split('=')[1] for x in parsed.query.split('&')}
            response = self.send_request(**kwargs)

            if isinstance(response, list):
                data.extend(response)
            elif isinstance(response.json(), dict):
                if 'values' in response.json():
                    if isinstance(response.json()['values'], list):
                        data.extend(response.json()['values'])
                    elif isinstance(response.json()['values'], dict):
                        data.update(response.json()['values'])
                else:
                    if isinstance(response.json(), list):
                        data.extend(response.json())
                    elif isinstance(response.json(), dict):
                        data.update(response.json())

        return data

    def read_remote_file(self, client, repo, file_path):
        """
        Get list of file as a particular path
        :param client:
        :param repo:
        :param file_path:
        :return:
        """
        if self.base in file_path:
            url = file_path
        else:
            url = urljoin(self.base, 'repositories', client, repo, file_path)
        return self.send_request(method="GET", url=url)

    def get_list_of_files(self, client, repo, path="tests"):
        """
        Get list of file as a particular path
        :param client:
        :param repo:
        :param path:
        :return:
        """
        url = urljoin(self.base, 'repositories', client, repo, re.sub(r"/$", "", path, re.I | re.M))
        return self.send_request(method="GET", url=url)

    def get_open_pull_requests(self, client, repo):
        """
        Get Open Pull Requests in Repository
        :param client:
        :param repo:
        """
        url = urljoin(self.base, 'repositories', client, repo, "pullrequests")
        params = {'state': 'OPEN', 'pagelen': 50}
        return self.send_request(method="GET", url=url, params=params)

    def get_pull_requests_statuses(self, client, repo, number):
        """
        Get Open Pull Requests in Repository
        :param client:
        :param repo:
        :param number:
        """
        url = urljoin(self.base, 'repositories', client, repo, f"pullrequests/{number}/statuses")
        return self.send_request(method="GET", url=url)

    def get_commits(self, client, repo):
        """
        Get Last 100 Commits
        :param client:
        :param repo:
        :return:
        """
        url = urljoin(self.base, 'repositories', client, repo, "commits/master")
        params = {'pagelen': 100, "page": 1}
        return self.send_request(method="GET", url=url, params=params)

    def get_repo_variables(self, client='company_name', repo=None):
        """
        Get Repo Variables
        :param client:
        :param repo:
        :return:
        """
        repo_variables = dict()
        if repo is None:
            raise Exception('Repo Name is mandatory !!')
        url = urljoin(self.base, 'repositories', client, repo, 'pipelines_config/variables/')
        content = self.send_request(method="GET", url=url)
        for _variable in content:
            if 'value' in _variable:
                repo_variables[_variable['key']] = _variable['value']
            else:
                repo_variables[_variable['key']] = None
        return repo_variables

    def get_parent_commit(self, client, repo, commit):
        """
        Get Parent Commit (to find out the difference)
        :param client:
        :param repo:
        :param commit:
        :return:
        """
        url = urljoin(self.base, 'repositories', client, repo, f"commit/{commit}")
        content = dict_to_ns(self.send_request(method="GET", url=url))
        return content.parents[0].hash[:7]

    def get_last_merged_pr_author(self, client, repo):
        """
        Get Emails Id of Last merged PR's Author
        :param client:
        :param repo:
        :return:
        """
        commits = dict_to_ns(self.get_commits(client, repo))
        for commit in commits:
            email = re.search(r"<(.*?)>", commit.author.raw, re.I | re.M).group(1)
            if str(email).endswith('company_name.com') and email not in ['test@test.com']:
                return [email]
        return ['test@test.com']

    def get_pr_author_email(self, client, repo, number):
        """
        Get author or Pull Request
        :return:
        """
        url = urljoin(self.base, 'repositories', client, repo, f"pullrequests/{number}/commits")
        content = dict_to_ns(self.send_request(method="GET", url=url))
        authors = set()
        for raw in [x.author.raw for x in content]:
            match = re.search(r".*<(.*?@test.com)>", raw)
            if match:
                authors.add(match.group(1))
        return list(authors)

    def upload_file_to_branch(self, client, repo):
        """
        Upload file to a bit bucket branch
        """
        url = urljoin(self.base, 'repositories', client, repo, "src/bitbucket-testing", "bitbucket.py")
        with open("bitbucket.py", "r") as fp:
            data = self.send_request(method="POST", url=url, files=fp)
        return data

    def get_commit_difference(self, client, repo, commit):
        """
        Get Difference in a Commit
        """
        url = urljoin(self.base, 'repositories', client, repo, f"commits/{commit}")
        content = dict_to_ns(self.send_request(method="GET", url=url))
        differences = []
        for _diff_url in [x.links.diff.href for x in content]:
            diff = self.send_request(method="GET", url=_diff_url)
            differences.append(diff)

        return differences

    def get_commit_file(self, client, repo, commit, file_name):
        """
        Get Commit File
        """
        url = urljoin(self.base, 'repositories', client, repo, f"src/{commit}/{file_name}")
        return self.send_request(method="GET", url=url)

    def get_tags(self, client, repo):
        """
        Get list of Tags in Repo (sorted in descending order of creation)
        :param client:
        :param repo:
        :return:
        """
        url = urljoin(self.base, 'repositories', client, repo, "refs/tags")
        params = {"sort": "-target.date"}
        values = self.send_request(method="GET", url=url, params=params)
        return values

    def get_all_project_keys(self, client='company_name'):
        """
        Get all Projects in company_name workspace
        :param client:
        :return:
        """
        params = {'pagelen': 100}
        url = urljoin(self.base, 'teams', client, "projects/")
        values = self.send_request(method="GET", url=url, params=params)
        return [x['key'] for x in values if 'key' in x and x['key'] != 'TEST']

    def get_all_repos(self, client='company_name', slug=True):
        """
        Get list of all Repos that are in company_name Workspace
        :param client:
        :param slug: Return Repo Slugs Only
        :return:
        """
        repos = list()
        for projectKey in self.get_all_project_keys():
            params = {'q': f"project.key=\"{projectKey}\"", 'pagelen': 100}
            url = urljoin(self.base, 'repositories', client)
            values = self.send_request(method="GET", url=url, params=params)
            repos.extend(values)

        if slug:
            return [x['slug'] for x in repos if 'slug' in x]
        else:
            return repos

    def get_branch_restrictions(self, client, repo):
        """
        Get Branch Restrictions
        :param client:
        :param repo:
        :return:
        """
        url = urljoin(self.base, 'repositories', client, repo, 'branch-restrictions')
        values = self.send_request(method="GET", url=url)
        return values

    def update_branch_restrictions(self, client, repo, rule_id, data):
        """
        Update Branch Restrictions
        :param client:
        :param repo:
        :param rule_id:
        :param data:
        :return:
        """
        url = urljoin(self.base, 'repositories', client, repo, 'branch-restrictions', rule_id)
        data = self.send_request(method="PUT", url=url, json=data)
        return data


if __name__ == "__main__":
    bb = BitBucketApi()
    p = bb.get_all_repos("company_name")
    print()
