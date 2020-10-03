__author__ = "sarvesh.singh"

import pytest


@pytest.mark.FLIPKART
@pytest.mark.run(order=1)
class TestFlipkart:
    """
    This suite is created to test and automate the flipkart flow
    """

    def test_01_launch_flipkart(self, web_driver, pages, resources):
        """
        Load flipkart website
        :param web_driver
        :param pages
        :param resources
        :return:
        """
        web_driver.open_website(url=resources.url.flipkart)
        web_driver.allure_attach_jpeg(file_name='homePage')
        pages.home.close_pop_up()

    def test_02_search_apple(self, pages, web_driver):
        """
        Search Apple mobiles
        :param pages
        :param web_driver
        :return:
        """
        pages.home.search_apple()
        pages.home.click_search()
        web_driver.allure_attach_jpeg(file_name='searchResults')

    def test_03_print_result(self, pages):
        """
        Print apple device name and price
        :param pages
        :return:
        """
        pages.search.print_search_results()
