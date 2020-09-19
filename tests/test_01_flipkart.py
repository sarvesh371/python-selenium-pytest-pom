__author__ = "sarvesh.singh"

from base.common import *


@pytest.mark.FLIPKART
@pytest.mark.run(order=1)
class TestFlipkart:
    """
    This suite is created to test and automate the flipkart flow
    """

    def test_01_launch_flipkart(self, web_driver, resources):
        """
        Load flipkart website
        :return:
        :param web_driver
        :param resources
        """
        web_driver.open_website(url=resources.url.flipkart.url)
        web_driver.allure_attach_jpeg("test")
