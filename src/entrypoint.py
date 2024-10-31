import os
import logging
from datetime import datetime, timedelta
from garmin_sync import GarminWeightTracker


def sync_last_n_days(tracker: GarminWeightTracker, days: int = 10):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    tracker.fetch_and_store_weight(start_date, end_date)


def sync_all_data(tracker: GarminWeightTracker):
    tracker.get_earliest_weight_data()


def main(use_fixture_data: bool = False):
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        logging.error(
            "Please set GARMIN_EMAIL and GARMIN_PASSWORD environment variables"
        )
        return

    if use_fixture_data:
        tracker = GarminWeightTracker()
    else:
        tracker = GarminWeightTracker(email, password)

    sync_last_n_days(tracker)


if __name__ == "__main__":
    main()
