__author__ = "sarvesh.singh"

from base.common import *

correlationId = generate_guid()


def update_authentication(func):
    """
    Decorator function to update auth type
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper_function(self, *args, **kwargs):
        """
        Wrapper Function to set authentication type and update header accordingly
        :param self:
        :param args:
        :param kwargs:
        :return:
        """
        if "auth" in kwargs:
            # Remove all authorizations from Header First
            if "authorization" in self.session.headers:
                del self.session.headers["authorization"]
            if "Authorization" in self.session.headers:
                del self.session.headers["Authorization"]

            # Update Basic Token
            if str(kwargs["auth"]).lower() == "basic":
                assert self.basicToken is not None, "ERROR: Basic Token is None !!"
                self.session.headers["Authorization"] = self.basicToken

            # Update Bearer Token
            elif str(kwargs["auth"]).lower() == "bearer":
                assert self.bearerToken is not None, "ERROR: Bearer Token is None !!"
                self.session.headers["Authorization"] = self.bearerToken

            else:
                pass

        # Execute the func and save it's response
        response = func(self, *args, **kwargs)

        return process_response(response)

    return wrapper_function


class SendRestRequest:
    """
    Class to send Rest Requests on a remote server
    """

    def __init__(self):
        """
        Init Function to get the Auth Token
        """
        global correlationId
        self.headers = dict()

        self.basicToken = None
        self.bearerToken = None
        self.userToken = None
        self.crewToken = None
        self.adminToken = None
        self.timeout = 60
        self.curlCommand = None
        self.logger = Logger(name="REST").get_logger

        self.logger.debug(f"correlationId: {correlationId}")
        os.environ["correlationId"] = correlationId

        self.session = requests.Session()
        self.session.verify = True

        # Adding Retries when there is a connect, redirect and read issue !!
        retries = HTTPAdapter(
            max_retries=Retry(total=2, connect=2, read=2, backoff_factor=0.5, status_forcelist=(422, 500, 502, 504), ),
        )
        # self.session.mount("http://", retries)
        # self.session.mount("https://", retries)

        pool = HTTPAdapter(
            pool_connections=int(os.environ.get("E2E_PERFORMANCE_COUNTS", 100)),
            pool_maxsize=int(os.environ.get("E2E_PERFORMANCE_COUNTS", 100)) * 10
        )
        self.session.mount("http://", pool)
        self.session.mount("https://", pool)

        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Accept"] = "*/*"
        self.session.headers["correlationId"] = correlationId

    @update_authentication
    def send_request(
            self,
            method,
            url,
            json=None,
            data=None,
            files=None,
            params=None,
            headers=None,
            stream=None,
            timeout=None,
            auth="Basic",
    ):
        """
        Send any Request
        :param method
        :param url
        :param json
        :param data
        :param files
        :param params
        :param headers
        :param stream
        :param timeout
        :param auth
        """
        method = str(method).upper()
        arguments = {
            "method": method,
            "url": url,
            "json": json,
            "files": files,
            "timeout": timeout,
            "data": data,
            "params": params,
            "stream": stream,
        }

        # Remove None Params, so that they are not sent with Final Call
        if data is None:
            del arguments["data"]
        if json is None:
            del arguments["json"]
        if files is None:
            del arguments["files"]
        if params is None:
            del arguments["params"]
        if stream is None:
            del arguments["stream"]
        if headers:
            self.session.headers.update(headers)
        if files:
            if "content-type" in self.session.headers:
                del self.session.headers["content-type"]
            if "Content-Type" in self.session.headers:
                del self.session.headers["Content-Type"]
        if timeout is None:
            timeout = self.timeout

        # Generate and save curl command
        for _skip in [
            "bitbucket.org",
            "slack.com",
            "atlassian.net",
        ]:
            if _skip in url:
                break
        else:
            if data:
                self.curlCommand = generate_curl_command(
                    method=method,
                    headers=self.session.headers,
                    url=url,
                    params=params,
                    data=data,
                )
            else:
                self.curlCommand = generate_curl_command(
                    method=method,
                    headers=self.session.headers,
                    url=url,
                    params=params,
                    data=json,
                )

        return self.perform_request(arguments=arguments)

    def perform_request(self, arguments):
        """
        Perform the Rest Request
        :param arguments:
        :return:
        """
        exception = None
        response = None
        try:
            response = self.session.request(**arguments)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            exception = err
        finally:
            if "files" in arguments:
                self.session.headers["Content-Type"] = "application/json"

            # if there is an exception, report it
            if exception:
                text = dict()
                if hasattr(exception, "response"):
                    # Capture Reason
                    if hasattr(exception.response, "reason"):
                        text["reason"] = exception.response.reason
                    # Capture Status Code
                    if hasattr(exception.response, "status_code"):
                        text["statusCode"] = exception.response.status_code
                    # Capture Text Message
                    if hasattr(exception.response, "text"):
                        text["message"] = exception.response.text
                    # Capture URL
                    if hasattr(exception.response, "url"):
                        text["url"] = exception.response.url
                    # Capture History (URL's Redirect)
                    if hasattr(exception.response, "history"):
                        if len(exception.response.history) > 0:
                            for history in exception.response.history:
                                text["url"] = history.url
                                break

                if len(text) > 0:
                    if not str(exception.response.url).split("/")[-1] in [
                        "info",
                        "version",
                    ]:
                        self.logger.error(text)
                    raise Exception(f"** {text} **")
                else:
                    raise Exception(f"** {exception} **")

            return response
