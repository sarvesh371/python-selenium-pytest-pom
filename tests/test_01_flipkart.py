__author__ = "sarvesh.singh"

from base.common import pytest


@pytest.mark.FLIPKART
@pytest.mark.run(order=1)
class TestFlipkart:
    """
    This suite is created to test and automate the flipkart flow
    """

    def test_01_launch_flipkart(self):
        """
        Load flipkart website
        :return:
        """
        print()
