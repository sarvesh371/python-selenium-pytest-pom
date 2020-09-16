__author__ = "sarvesh.singh"

from datetime import datetime, timedelta
from pytz import timezone
from testrail_api import TestRailAPI
from base.common import get_resource_config


class TestRailApi(TestRailAPI):
    """
    Class to Perform Test-Rails Cleanup
    """

    def __init__(self):
        self.resource = get_resource_config()
        super().__init__(
            url=self.resource.test_rails.url,
            email=self.resource.test_rails.email,
            password=self.resource.test_rails.api_key,
            retry=10,
        )
        self.project_id = 1

    def get_plans_to_clean(self, before_days=2, is_completed=0):
        """
        Get Plans to be cleaned
        :param before_days:
        :param is_completed:
        :return:
        """
        created_before = (
                datetime.now(tz=timezone("Asia/Kolkata")) - timedelta(days=before_days)
        ).strftime("%s")
        plans = self.plans.get_plans(
            project_id=self.project_id,
            created_before=created_before,
            is_completed=is_completed,
        )
        while len(plans) % 250 == 0:
            offset = len(plans)
            next_plans = self.plans.get_plans(
                project_id=self.project_id,
                created_before=created_before,
                offset=offset,
                is_completed=is_completed,
            )
            if len(next_plans) == 250:
                plans.extend(next_plans)
                continue
            else:
                plans.extend(next_plans)
                break
        return plans
