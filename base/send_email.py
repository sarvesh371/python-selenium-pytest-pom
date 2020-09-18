__author__ = "sarvesh.singh"

from base.common import base64_decode
from email.message import EmailMessage
import smtplib


class SendEmail:
    """
    Class to send email using smtplib package
    """

    def __init__(
            self, username=None, password=None, host="smtp.office365.com", port=587
    ):
        """
        init function which needs username and password
        :param username:
        :param password:
        :param host:
        :param port:
        """
        self.username = username
        self.password = password
        if self.username is None or self.password is None:
            self.encoded = "Yhskssuskowpwkwshsbshss="
            self.username, self.password = base64_decode(self.encoded)
        self.host = host
        self.port = port
        self.server = self.connect()

    def connect(self):
        """
        Connect to mail server
        :return:
        """
        mail_server = smtplib.SMTP(host=self.host, port=self.port)
        mail_server.ehlo()
        mail_server.starttls()
        mail_server.ehlo()
        mail_server.login(user=self.username, password=self.password)
        return mail_server

    def send_mail(self, from_address="test@test.com", to_address=None, message=None):
        """
        Send email now
        :param from_address:
        :param to_address:
        :param message:
        :return:
        """
        msg = EmailMessage()
        msg["From"] = from_address
        msg["To"] = to_address
        msg["Subject"] = "Test-Email"
        msg.set_content(message)
        self.server.send_message(msg)

    def __del__(self):
        """
        Destructor
        :return:
        :rtype:
        """
        self.server.close()
