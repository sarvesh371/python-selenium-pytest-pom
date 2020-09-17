__author__ = "sarvesh.singh"

from jira import JIRA


class Jira:
    """
    Class to play with Jira Ticketing System
    """

    def __init__(self, user, api_key):
        """
        Connect to Jira etc.
        :param user:
        :param api_key:
        """
        self.user = user
        self.api_key = api_key
        self.basic_auth = (self.user, self.api_key)
        self.epic_link = "customfield_1010"

        # Static Variables
        self.epic = "TXP-1"
        self.project_name = "TXP"

        # To Be Used Variables
        self.project = None
        self.project_id = None
        self.fields = None
        self.jira = JIRA(server="https://companyName.atlassian.net/", basic_auth=self.basic_auth, timeout=30)

        # Always Run these functions
        self._issue_fields(self.epic)
        self._connect_to_project(self.project_name)

    def _connect_to_project(self, name):
        """
        Connect to a Project
        :param name:
        :return:
        """
        for project in self.jira.projects():
            if project.key == name:
                self.project_id = project.id
                break

        self.project = self.jira.project(self.project_id)

    def get_user_name(self, user):
        """
        Get User Name from give user (in Jira Structure)
        :param user:
        :return:
        """
        _user_name = str(user).split("@")[0]
        if len(_user_name.split(".")) <= 1:
            raise Exception(f"Wrong username '{user}'")
        for _users in self.jira.search_users(_user_name.split(".")[0]):
            if _user_name == _users.key:
                return _users.name, _users.accountId
        raise Exception(f"ERROR: No matching user found {user} !!")

    def delete_issue(self, issue):
        """
        Delete and issue
        :param issue:
        :return:
        """
        self.jira.issue(issue).delete()

    def _issue_fields(self, sample):
        """
        Get Fields in an issue
        :param sample:
        :return:
        """
        issue = self.jira.issue(sample)
        self.fields = issue.fields

    def get_issue_details(self, issue):
        """
        Get issue details
        :param issue:
        :return:
        """
        issue_data = self.jira.issue(issue, fields="summary,description,assignee,issuetype,customfield_1010")
        return issue_data

    def get_open_component_bugs(self, summary):
        """
        Get all Open Bugs in Project
        :param summary:
        :return:
        """
        query = f'status NOT IN ("Closed", "Done", "Rejected") AND summary ~ "{summary}"'
        _result = self._run_query(query)
        if _result.total > 0:
            return _result.iterable[0].key
        else:
            return None

    def get_resolved_components_bug(self, summary):
        """
        Get all resolved Bugs in Project
        :param summary:
        :return:
        """
        query = f'status IN ("Resolved") AND summary ~ "{summary}"'
        _result = self._run_query(query)
        if _result.total > 0:
            return _result.iterable[0].key
        else:
            return None

    def get_all_open_bugs(self):
        """
        Get all Open Bugs in Project
        :return:
        """
        _result = self._run_query('status NOT IN ("Closed", "Done", "Rejected")')
        if _result.total > 0:
            return _result.iterable[0].key
        else:
            return None

    def _run_query(self, query):
        """
        Function to run Query on Jira
        :param query:
        :return:
        """
        query = f'project = "{self.project_name}" AND {query}'
        _result = self.jira.search_issues(query)
        return _result

    def check_comp_ticket_is_open(self, summary):
        """
        Get if component ticket is already open
        :param summary:
        :return:
        """
        issues = self.get_open_component_bugs(summary)
        return issues

    def get_statuses(self):
        """
        Get the all status of JIRA
        :return:
        """
        return self.jira.statuses()
