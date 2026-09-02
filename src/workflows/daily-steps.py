from datetime import date, timedelta

from dotenv import load_dotenv

from src.helpers import get_garmin_client, get_notion_client


def get_all_daily_steps(garmin):
    """
    Get yesterday's daily step count from Garmin Connect.
    """
    yesterday = date.today() - timedelta(days=1)

    return garmin.get_daily_steps(
        yesterday.isoformat(),
        yesterday.isoformat()
    )


def daily_steps_exist(client, database_id, activity_date):
    """
    Check if daily step count already exists in Notion.
    """
    query = client.databases.query(
        database_id=database_id,
        filter={
            "property": "Date",
            "date": {"equals": activity_date}
        }
    )

    results = query["results"]
    return results[0] if results else None


def update_daily_steps(client, existing_steps, new_steps):
    """
    Update an existing daily steps entry.
    """
    properties = {
        "Date": {
            "date": {
                "start": new_steps.get("calendarDate")
            }
        },
        "Steps": {
            "number": new_steps.get("totalSteps")
        }
    }

    client.pages.update(
        page_id=existing_steps["id"],
        properties=properties
    )


def create_daily_steps(client, database_id, steps):
    """
    Create a new daily steps entry in Notion.
    """
    properties = {
        "Date": {
            "date": {
                "start": steps.get("calendarDate")
            }
        },
        "Steps": {
            "number": steps.get("totalSteps")
        }
    }

    page = {
        "parent": {
            "database_id": database_id
        },
        "properties": properties
    }

    client.pages.create(**page)


def main():
    load_dotenv()

    garmin_client, _ = get_garmin_client()
    notion_client, notion_dbs = get_notion_client()

    database_id = notion_dbs.daily_steps

    daily_steps = get_all_daily_steps(garmin_client)

    for steps in daily_steps:
        steps_date = steps.get("calendarDate")

        existing_steps = daily_steps_exist(
            notion_client,
            database_id,
            steps_date
        )

        if existing_steps:
            update_daily_steps(
                notion_client,
                existing_steps,
                steps
            )
            print(f"Updated: {steps_date} - {steps.get('totalSteps')} steps")
        else:
            create_daily_steps(
                notion_client,
                database_id,
                steps
            )
            print(f"Created: {steps_date} - {steps.get('totalSteps')} steps")


if __name__ == "__main__":
    main()