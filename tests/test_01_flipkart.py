__author__ = "sarvesh.singh"

from base.common import *
from pages.home_page import HomePage
from pages.search_results import SearchResults


@pytest.mark.FLIPKART
@pytest.mark.run(order=1)
class TestFlipkart:
    """
    This suite is created to test and automate the flipkart flow
    """

    def test_01_launch_flipkart(self, web_driver, page, resources):
        """
        Load flipkart website
        :return:
        :param web_driver
        :param page
        :param resources
        """
        setattr(page, 'home', HomePage(web_driver))
        setattr(page, 'search', SearchResults(web_driver))
        web_driver.open_website(url=resources.url.flipkart)
        web_driver.allure_attach_jpeg(file_name='homePage')
        page.home.close_pop_up()

    def test_02_search_apple(self, page, web_driver):
        """
        Search Apple mobiles
        :return:
        :param page
        :param web_driver
        """
        page.home.search_apple()
        page.home.click_search()
        web_driver.allure_attach_jpeg(file_name='searchResults')

    def test_03_write_result_file(self, page):
        """
        Create a file and write all results in a file with name and price
        :return:
        :param page
        """
        page.search.print_search_results()
