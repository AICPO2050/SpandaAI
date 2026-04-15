import os
import requests
from dotenv import load_dotenv

load_dotenv()

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
LINEAR_API_URL = "https://api.linear.app/graphql"

headers = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json"
}

def get_team_id():
    query = {"query": "{ teams { nodes { id name } } }"}
    response = requests.post(LINEAR_API_URL, json=query, headers=headers)
    teams = response.json()["data"]["teams"]["nodes"]
    return teams[0]["id"]

def create_ticket(title, description, team_id):
    mutation = {
        "query": f"""
        mutation {{
            issueCreate(input: {{
                title: "{title}",
                description: "{description}",
                teamId: "{team_id}"
            }}) {{
                success
                issue {{
                    id
                    title
                    url
                }}
            }}
        }}
        """
    }
    response = requests.post(LINEAR_API_URL, json=mutation, headers=headers)
    return response.json()

if __name__ == "__main__":
    print("Testing Linear connection...")
    team_id = get_team_id()
    print(f"Team ID: {team_id}")
    
    result = create_ticket(
        "ACH Onboarding - Self Service Portal",
        "As a business customer, I want to complete ACH onboarding online through BusinessExpress.",
        team_id
    )
    print("Ticket created!")
    print(result)