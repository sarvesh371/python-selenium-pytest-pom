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
            "closePopUp": "//*[@class='_2AkmmA _29YdH8']",
            "searchBox": "//input[@class='LM6RPg']",
            "searchButton": "//button[@class='vh79eN']",
        })

    def close_pop_up(self):
        """
        Close the signup pop up
        :return:
        """
        self.webDriver.click(element=self.locators.closePopUp, locator_type='xpath')

    def search_apple(self):
        """
        Search Apple
        :return:
        """
        self.webDriver.set_text(element=self.locators.searchBox, locator_type='xpath', text='apple')

    def click_search(self):
        """
        Click the search button
        :return:
        """
        self.webDriver.click(element=self.locators.searchButton, locator_type='xpath')
