import schedule
import time
from garmin_sync import GarminWeightTracker


def main():
    tracker = GarminWeightTracker()
    client = tracker.connect_to_garmin(
        os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD")
    )
    if client:
        tracker.fetch_and_store_weight(client)


schedule.every().day.at("09:00").do(main)

while True:
    schedule.run_pending()
    time.sleep(1)
