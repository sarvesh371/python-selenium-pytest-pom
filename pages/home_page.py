__author__ = "sarvesh.singh"

from base.common import dict_to_ns


class HomePage:
    """
    Class for contains methods of Home Page
    """

    def __init__(self, web_driver):
        """
        To Initialize the locators of Home page
        :param web_driver
        """
        self.webDriver = web_driver
        self.locators = dict_to_ns({
            "loader": "//div[@class='']",
        })

    def close_pop_up(self):
        """
        Close the signup pop up
        :return:
        """
        print()

