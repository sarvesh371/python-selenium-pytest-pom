__author__ = "sarvesh.singh"
"""
Library to talk to Confluence and make changes etc.
"""
import re
from base.common import base64_encode, urljoin
from base.rest import SendRestRequest


class Confluence(SendRestRequest):
    """
    Main Class to connect to Confluence
    """

    def __init__(self, username, token):
        """
        Init Class to make a connection with Confluence Server
        :param username:
        :param token:
        """
        super().__init__()
        self.base_url = "https://companyName.atlassian.net/wiki/rest/api/content"
        self.username = username
        self.token = token
        self.headers = {
            "Authorization": f"Basic {base64_encode(username=self.username, password=self.token)}",
            "contentType": "application/json",
        }
        self.session.headers.update(self.headers)

    def get_document(self, document_id):
        """
        Get Document Details using Document ID
        :param document_id:
        :return:
        :rtype:
        """
        params = {"expand": "space,body.storage,ancestors,version"}
        url = urljoin(self.base_url, str(document_id))
        data = self.send_request(method="GET", url=url, params=params).content
        return data

    def copy_document(self, source_id, new_name=None):
        """
        Copy a Document with given Source ID
        :param source_id:
        :param new_name:
        :return:
        :rtype:
        """
        original = self.get_document(source_id)
        if new_name is None:
            original["title"] = f"{original['title']} - (Copy)"
        else:
            original["title"] = new_name
        data = self.send_request(
            method="POST", url=self.base_url, json=original
        ).content
        return f"{data['_links']['base']}{data['_links']['webui']}"

    def copy_replace_document(self, source_id, new_name=None, replace=None):
        """
        Copy a document with replacing some fields in it
        :param source_id:
        :param new_name:
        :param replace:
        :return:
        :rtype:
        """
        if replace is None:
            replace = {}
        if not isinstance(replace, dict):
            raise Exception(f"{replace} has to be key-value (dict) pairs !!")
        original = self.get_document(source_id)
        if new_name is None:
            original["title"] = f"{original['title']} - (Copy)"
        else:
            original["title"] = new_name
        # Do Replacing (to be strict)
        value = original["body"]["storage"]["value"]
        for _replace in replace:
            replace_with = replace[_replace]
            value = re.sub(
                r"{}".format(_replace),
                r"{}".format(replace_with),
                value,
                flags=re.I | re.M,
            )
        original["body"]["storage"]["value"] = value
        data = self.send_request(
            method="POST", url=self.base_url, json=original
        ).content
        return f"{data['_links']['base']}{data['_links']['webui']}"

    def update_document(self, document_id, req_body):
        """
        Update the confluence Page
        :param document_id:
        :return:
        :rtype:
        """
        params = {"status": "draft", "action": "publish"}
        url = urljoin(self.base_url, str(document_id))
        status = self.send_request(method="PUT", url=url, json=req_body, params=params)
        if status.status_code != 200:
            raise Exception(
                f'Failed to Update the Page Reason {status.content["body"]}'
            )
