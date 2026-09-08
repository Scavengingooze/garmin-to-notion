from datetime import datetime

import pytz
from dotenv import load_dotenv

from src.helpers import get_garmin_client, get_notion_client


# Constants
local_tz = pytz.timezone("Europe/Zurich")


def get_sleep_data(garmin):
    today = datetime.today().date()
    return garmin.get_sleep_data(today.isoformat())


def format_duration(seconds):
    """
    Convert seconds into a readable duration.
    Example: 27120 -> '7h 32m'
    """
    minutes = (seconds or 0) // 60
    return f"{minutes // 60}h {minutes % 60}m"


def format_time_readable(timestamp):
    """
    Convert Garmin timestamp (milliseconds) to local Zurich time.
    Example: 1724017320000 -> '23:42'
    """
    return (
        datetime.fromtimestamp(timestamp / 1000, local_tz).strftime("%H:%M")
        if timestamp
        else "Unknown"
    )


def format_date_for_name(sleep_date):
    """
    Convert YYYY-MM-DD to DD.MM.YYYY.
    Example: 2026-08-28 -> 28.08.2026
    """
    return (
        datetime.strptime(sleep_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        if sleep_date
        else "Unknown"
    )


def sleep_data_exists(client, database_id, sleep_date):
    """
    Check whether a sleep entry for the given date already exists.
    The Date property is the Notion title property.
    """
    date_name = format_date_for_name(sleep_date)

    query = client.databases.query(
        database_id=database_id,
        filter={
            "property": "Date",
            "title": {
                "equals": date_name
            }
        }
    )

    results = query.get("results", [])

    return results[0] if results else None


def create_sleep_data(client, database_id, sleep_data, skip_zero_sleep=True):
    """
    Create a new sleep entry in the Notion Sleep Data database.
    """

    daily_sleep = sleep_data.get("dailySleepDTO", {})

    if not daily_sleep:
        print("No daily sleep data found.")
        return

    sleep_date = daily_sleep.get("calendarDate")

    if not sleep_date:
        print("No sleep date found.")
        return

    # Calculate total sleep from the three sleep stages.
    total_sleep = sum(
        (daily_sleep.get(key, 0) or 0)
        for key in [
            "deepSleepSeconds",
            "lightSleepSeconds",
            "remSleepSeconds",
        ]
    )

    # Do not create an entry if Garmin reports zero sleep.
    if skip_zero_sleep and total_sleep == 0:
        print(
            f"Skipping sleep data for {sleep_date} "
            "as total sleep is 0."
        )
        return

    properties = {
        "Date": {
            "title": [
                {
                    "text": {
                        "content": format_date_for_name(sleep_date)
                    }
                }
            ]
        },

        "Ora inizio": {
            "rich_text": [
                {
                    "text": {
                        "content": format_time_readable(
                            daily_sleep.get("sleepStartTimestampGMT")
                        )
                    }
                }
            ]
        },

        "Ora fine": {
            "rich_text": [
                {
                    "text": {
                        "content": format_time_readable(
                            daily_sleep.get("sleepEndTimestampGMT")
                        )
                    }
                }
            ]
        },

        "Total Sleep": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(total_sleep)
                    }
                }
            ]
        },

        "Light Sleep": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("lightSleepSeconds", 0)
                        )
                    }
                }
            ]
        },

        "Deep Sleep": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("deepSleepSeconds", 0)
                        )
                    }
                }
            ]
        },

        "REM Sleep": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("remSleepSeconds", 0)
                        )
                    }
                }
            ]
        },

        "Awake Time": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("awakeSleepSeconds", 0)
                        )
                    }
                }
            ]
        },

        "Resting HR": {
            "number": sleep_data.get("restingHeartRate", 0)
        },
    }

    client.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        icon={"emoji": "😴"},
    )

    print(f"Created sleep entry for: {sleep_date}")


def main():
    load_dotenv()

    print("Starting sleep data sync...")

    # Initialize Garmin and Notion clients.
    garmin_client, _ = get_garmin_client()
    notion_client, notion_dbs = get_notion_client()

    # Get Sleep Data database ID.
    database_id = notion_dbs.sleep

    print(f"Using Sleep Data database: {database_id}")

    # Get today's sleep data from Garmin.
    data = get_sleep_data(garmin_client)

    if not data:
        print("No sleep data returned by Garmin.")
        return

    sleep_date = data.get("dailySleepDTO", {}).get("calendarDate")

    if not sleep_date:
        print("Garmin returned sleep data without a calendar date.")
        return

    print(f"Sleep data found for: {sleep_date}")

    # Check whether this date already exists in Notion.
    existing_entry = sleep_data_exists(
        notion_client,
        database_id,
        sleep_date,
    )

    if existing_entry:
        print(
            f"Sleep entry for {sleep_date} already exists. "
            "Skipping creation."
        )
        return

    # Create the Notion entry.
    create_sleep_data(
        notion_client,
        database_id,
        data,
        skip_zero_sleep=True,
    )


if __name__ == "__main__":
    main()