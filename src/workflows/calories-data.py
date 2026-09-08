from datetime import datetime

from dotenv import load_dotenv

from src.helpers import get_garmin_client, get_notion_client

from datetime import datetime, timedelta


def get_daily_calories(garmin):
    yesterday = datetime.today().date() - timedelta(days=1)
    return garmin.get_user_summary(yesterday.isoformat())


def format_date(date_string):
    return datetime.strptime(
        date_string,
        "%Y-%m-%d",
    ).strftime("%d.%m.%Y")


def daily_calories_exists(client, database_id, date_string):
    query = client.databases.query(
        database_id=database_id,
        filter={
            "property": "Date",
            "title": {
                "equals": format_date(date_string),
            },
        },
    )

    results = query.get("results", [])

    return results[0] if results else None


def create_daily_calories(
    client,
    database_id,
    calories_data,
):
    date_string = calories_data.get("calendarDate")

    if not date_string:
        print("No calendar date found.")
        return

    resting_calories = calories_data.get(
        "bmrKilocalories",
        0,
    ) or 0

    active_calories = calories_data.get(
        "activeKilocalories",
        0,
    ) or 0

    total_calories = calories_data.get(
        "totalKilocalories",
        0,
    ) or 0

    properties = {
        "Date": {
            "title": [
                {
                    "text": {
                        "content": format_date(date_string),
                    }
                }
            ]
        },
        "Resting Calories": {
            "number": round(resting_calories),
        },
        "Active Calories": {
            "number": round(active_calories),
        },
        "Total Calories": {
            "number": round(total_calories),
        },
    }

    client.pages.create(
        parent={
            "database_id": database_id,
        },
        properties=properties,
        icon={
            "emoji": "🔥",
        },
    )

    print(
        f"Created calorie entry for {date_string}: "
        f"resting={round(resting_calories)}, "
        f"active={round(active_calories)}, "
        f"total={round(total_calories)}"
    )


def main():
    load_dotenv()

    print("Starting daily calories sync...")

    garmin_client, _ = get_garmin_client()
    notion_client, notion_dbs = get_notion_client()

    database_id = notion_dbs.daily_calories

    print(
        f"Using Daily Calories database: {database_id}"
    )

    data = get_daily_calories(garmin_client)

    if not data:
        print("No calorie data returned by Garmin.")
        return

    date_string = data.get("calendarDate")

    if not date_string:
        print(
            "Garmin returned calorie data "
            "without a calendar date."
        )
        return

    print(
        f"Calorie data found for: {date_string}"
    )

    existing_entry = daily_calories_exists(
        notion_client,
        database_id,
        date_string,
    )

    if existing_entry:
        print(
            f"Calorie entry for {date_string} "
            "already exists. Skipping creation."
        )
        return

    create_daily_calories(
        notion_client,
        database_id,
        data,
    )


if __name__ == "__main__":
    main()