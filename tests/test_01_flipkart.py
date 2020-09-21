__author__ = "sarvesh.singh"

from base.common import *


@pytest.mark.FLIPKART
@pytest.mark.run(order=1)
class TestFlipkart:
    """
    This suite is created to test and automate the flipkart flow
    """

    def test_01_launch_flipkart(self, web_driver, pages, resources):
        """
        Load flipkart website
        :return:
        :param web_driver
        :param pages
        :param resources
        """
        web_driver.open_website(url=resources.url.flipkart)
        web_driver.allure_attach_jpeg(file_name='homePage')
        pages.home.close_pop_up()

    def test_02_search_apple(self, pages, web_driver):
        """
        Search Apple mobiles
        :return:
        :param pages
        :param web_driver
        """
        pages.home.search_apple()
        pages.home.click_search()
        web_driver.allure_attach_jpeg(file_name='searchResults')

    def test_03_write_result_file(self, pages):
        """
        Create a file and write all results in a file with name and price
        :return:
        :param pages
        """
        pages.search.print_search_results()
