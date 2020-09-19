__author__ = "sarvesh.singh"

from base.common import *


@pytest.mark.FLIPKART
@pytest.mark.run(order=1)
class TestFlipkart:
    """
    This suite is created to test and automate the flipkart flow
    """

    def test_01_launch_flipkart(self, web_driver):
        """
        Load flipkart website
        :return:
        """
        web_driver.open_website(url='')
