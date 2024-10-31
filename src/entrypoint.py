import os
import logging
import argparse
from datetime import datetime, timedelta
from garmin_sync import GarminWeightTracker


def sync_last_n_days(tracker: GarminWeightTracker, days: int = 10):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    tracker.fetch_and_store_weight(start_date, end_date)


def sync_all_data(tracker: GarminWeightTracker):
    tracker.get_earliest_weight_data()


def main():
    parser = argparse.ArgumentParser(description='Sync weight data from Garmin Connect')
    parser.add_argument('--sync-type', 
                       choices=['recent', 'all'],
                       default='recent',
                       help='Type of sync: "recent" for last N days, "all" for all data')
    parser.add_argument('--days', 
                       type=int,
                       default=10,
                       help='Number of days to sync for recent sync type (default: 10)')
    args = parser.parse_args()

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        logging.error(
            "Please set GARMIN_EMAIL and GARMIN_PASSWORD environment variables"
        )
        return

    tracker = GarminWeightTracker(email, password)
    tracker.connect_to_garmin()

    if args.sync_type == 'recent':
        sync_last_n_days(tracker, args.days)
    else:
        sync_all_data(tracker)


if __name__ == "__main__":
    main()
