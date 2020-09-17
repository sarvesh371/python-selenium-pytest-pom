__author__ = "sarvesh.singh"

from slack import WebClient
from slack.errors import SlackApiError
from base.common import *


class SlackNotification(WebClient):
    """
    Slack Web Client to send slack messages
    """

    def __init__(self):
        """
        Slack Web Client Init Function
        """
        self.logger = basic_logging()
        token = os.environ.get("SLACK_API_TOKEN", None)
        if token is None:
            token = getattr(get_resource_config(), "slack_token")

        if token is None:
            raise Exception(
                "Set SLACK_API_TOKEN Environment Variable as Slack API Token"
            )

        super().__init__(token=token)

    def get_user_from_email(self, email, return_id=True, formatted=False):
        """
        Get User Lists
        :param email:
        :param return_id: Return only ID
        :param formatted: Return formatted so that it can be directly used
        :return:
        """
        try:
            data = self.users_lookupByEmail(email=email).data["user"]
            if return_id and formatted:
                return f"<@{data['id']}>"
            elif return_id and not formatted:
                return data["id"]
            else:
                return data
        except (SlackApiError, ValueError, Exception) as exp:
            raise Exception(f"Cannot Find user with email {email} | {exp}")

    def groups_to_tag(self, groups=None):
        """
        Get Groups who are to be tagged in the message that is being sent
        :param groups:
        :return:
        """
        data = []
        if groups is None or len(groups) == 0:
            return []
        for user in self.usergroups_list().data["usergroups"]:
            if user["handle"] in groups:
                data.append(user["id"])

        return " ".join([f"<!subteam^{x}>" for x in data])

    def send_message(self, message, channel=None, user=None, groups=None):
        """
        Send a message to a user of a group, either of channel or user is mandatory
        :param message: Message to be sent
        :param channel: Channel to which message has to be sent
        :param user: User to whom 1:1 message has to be sent, should be email id
        :param groups: Groups to tag the message
        :return:
        """
        if groups is not None:
            msg = self.groups_to_tag(groups)
            message = f"{msg} {message}"

        if user is None and channel is None:
            raise Exception(f"at-least one of user and channel is required")
        if user:
            if "@" not in user:
                self.logger.debug(f"{user} was without @ so appending @test.com")
                user = f"{user}@test.com"
            try:
                channel = self.get_user_from_email(user)
            except (SlackApiError, ValueError, Exception):
                raise Exception(f"Problem with {user}")

        self.chat_postMessage(channel=channel, text=message)

    def get_channel_id_from_channel_name(self, channel):
        """
        Get Channel ID from Channel Name using pagination
        :param channel:
        :return:
        """
        all_channels = []
        cursor = None
        conversation_list = self.users_conversations(
            exclude_archived=True, types="public_channel,private_channel", limit=1000
        ).data
        all_channels.extend(conversation_list["channels"])
        while cursor != "" or cursor is None:
            cursor = conversation_list["response_metadata"]["next_cursor"]
            for lst in all_channels:
                if lst["name"] == channel:
                    return lst["id"]
            conversation_list = self.conversations_list(
                exclude_archived=True, cursor=cursor, limit=1000
            ).data
            cursor = conversation_list["response_metadata"]["next_cursor"]
            all_channels.extend(conversation_list["channels"])
        else:
            raise Exception(f"Channel Name not found or not member !!")

    def send_file(self, name, message, channel=None, user=None, groups=None):
        """
        Send a file to user/channel
        :param name: File name to be sent
        :param message: message to be sent along with file
        :param channel: channel to whom it has to be sent
        :param user: user to whom it has to be sent
        :param groups: groups to tag
        :return:
        """
        if groups is not None:
            msg = self.groups_to_tag(groups)
            message = f"{msg} {message}"

        if user is None and channel is None:
            raise Exception(f"at-least one of user and channel is required")

        if user:
            if "@" not in user:
                self.logger.debug(f"{user} was without @ so appending @test.com")
                user = f"{user}@test.com"

            self.logger.debug(
                f"Send File {name} with message {message} to user: {user}"
            )
            try:
                channel = self.get_user_from_email(user)
            except (SlackApiError, ValueError, Exception) as exp:
                raise Exception(f"Problem with {user}")

        if channel:
            self.logger.debug(
                f"Send File {name} with message {message} to channel: {channel}"
            )
            channel = self.get_channel_id_from_channel_name(channel)

        self.files_upload(
            file=os.path.abspath(name),
            fileName=name,
            initial_comment=message,
            channels=channel,
        )


if __name__ == "__main__":
    s = SlackNotification()
    s.send_file(name="requirements.txt", message="Test Message", channel="test-channel")
    u = s.get_user_from_email('sarvesh.singh@test.com')
    s.send_message(message='Hi !!', channel='test-slack', groups=['test-group'])
    s.send_file(
        name="requirements.txt",
        message="Hi !!",
        channel="test-slack",
        groups=["test-group"],
    )
