import requests
import datetime
import os
from dotenv import load_dotenv
load_dotenv()
# Load API keys from environment variables



NOTION_API_KEY = os.getenv("NOTION_API_KEY")  # Store in GitHub Secrets
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")  # Now dynamically assigned
#DATABASE_ID = "8d5d28a856064783ad5adadf2c49b603" # You need to change this depending on your database
# Notion will give you this really long link: https://www.notion.so/8d5d28a856064783ad5adadf2c49b603?v=4ce8edb545e644209686c852a37425f3
#You need to extract the alphanumeric part between / and ? to get the DATABASE_ID
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # You use this for specifying the channel, store the key in your secrets

# Notion API Headers
print(NOTION_API_KEY)
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def get_tasks():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    # Get the date 7 days ago
    last_week = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

    payload = {
        "filter": {
            "property": "Last Modification",
            "date": {
                "on_or_after": last_week
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        print(" Error fetching tasks:", response.json())
        return []

    tasks = response.json().get("results", [])
    return tasks



# Format tasks into a weekly report

def format_report(tasks):
    report_date = datetime.date.today().strftime("%Y-%m-%d")

    # Lists to store categorized tasks
    ongoing_tasks = []
    completed_tasks = []

    # Get the date 7 days ago
    last_week = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

    for task in tasks:
        # Extract relevant properties safely
        task_name = task['properties']['Task name']['title'][0]['text']['content'] if (
            'Task name' in task['properties'] and task['properties']['Task name']['title']
        ) else "Untitled Task"

        status = task['properties']['Status']['status']['name'] if (
            'Status' in task['properties'] and task['properties']['Status']['status']
        ) else "Unknown"

        assignee = task['properties']['Assignee']['people'][0]['name'] if (
            'Assignee' in task['properties'] and task['properties']['Assignee']['people']
        ) else "Unassigned"

        project = task['properties']['Project']['relation'][0]['id'] if (
            'Project' in task['properties'] and task['properties']['Project']['relation']
        ) else "No Project"

        due_date = task['properties']['Due']['date']['start'] if (
            'Due' in task['properties'] and task['properties']['Due']['date']
        ) else "No Due Date"

        last_modified = task['properties']['Last Modification']['date']['start'] if (
            'Last Modification' in task['properties'] and task['properties']['Last Modification']['date']
        ) else None

        # Format task info
        task_info = f"- *{task_name}* | 👤 {assignee} | 🏗 {project} | 📅 {due_date}"

        # Categorize tasks based on status
        if status.lower() in ["in progress", "ongoing"]:  # Adjust based on your actual Notion status names
            ongoing_tasks.append(task_info)
        elif status.lower() in ["completed", "done"]:  # Adjust as needed
            if last_modified and last_modified >= last_week:  # Only include tasks completed this week
                completed_tasks.append(task_info)

    # Build report text
    report_text = f"""
📊 *Weekly Report - {report_date}*

⏳ *Ongoing Tasks:*
{chr(10).join(ongoing_tasks) or "No ongoing tasks this week."}

✅*Completed Tasks (Updated This Week):*
{chr(10).join(completed_tasks) or "No tasks completed this week."}
    """

    return report_text.strip()


# Create a new Notion page for the report
def create_notion_report(report_text):
    url = "https://api.notion.com/v1/pages"

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Task name": {  #  Uses your actual "Task name" property
                "title": [{"text": {"content": f"Weekly Report - {datetime.date.today()}"}}]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": report_text}}]  #  Fix: Added `rich_text`
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()

# Send the report to Slack
def send_to_slack(report_text):
    if not SLACK_WEBHOOK_URL:
        print("Slack Webhook URL not found, skipping Slack notification.")
        return (None, None)  # Fix unpacking error

    message = {"text": report_text}
    response = requests.post(SLACK_WEBHOOK_URL, json=message)

    return response.status_code, response.text


# Run the script
if __name__ == "__main__":
    tasks = get_tasks()
    report_text = format_report(tasks)
    
    # Create Notion report
    # notion_response = create_notion_report(report_text)
    # print("✅ Notion report created:", notion_response)

    # Send to Slack (optional)
    if report_text:
        slack_status, slack_response = send_to_slack(report_text)
        print(f"✅ Slack response: {slack_status} - {slack_response}")
    else:
        print("No tasks to report, skipping Slack notification.")
