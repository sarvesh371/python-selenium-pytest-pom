__author__ = "sarvesh.singh"

from base.common import *
from pages.home_page import HomePage


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
        web_driver.open_website(url=resources.url.flipkart.url)
        page.home.close_pop_up()
