__author__ = "sarvesh.singh"

from base.common import dict_to_ns
from base.logger import Logger


class SearchResults:
    """
    Class for contains methods of Search Results Page
    """

    def __init__(self, web_driver):
        """
        To Initialize the locators of Search Results page
        :param web_driver
        """
        self.webDriver = web_driver
        self.locators = dict_to_ns({
            "resultsName": "//*[@class='_2cLu-l']",
            "resultsPrice": "%s/../a[3]/div/div[1]",
            "searchResultsPage": "//span[contains(text(), 'Showing ')]",
        })
        self.logger = Logger(name="RESULTS").get_logger

    def print_search_results(self):
        """
        print the search results in console
        :return:
        """
        self.webDriver.explicit_visibility_of_element(element=self.locators.searchResultsPage, locator_type='xpath',
                                                      time_out=60)
        results_name = self.webDriver.get_elements(element=self.locators.resultsName, locator_type='xpath')
        results_price = self.webDriver.get_elements(element=self.locators.resultsPrice % self.locators.resultsName,
                                                    locator_type='xpath')
        for _result in results_name:
            name = _result.text
            price = results_price[results_name.index(_result)].text
            self.logger.info(f'Device Name - {name} | Price - {price}')
