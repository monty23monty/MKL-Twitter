import json

from openai import OpenAI
import requests

prompt = "Generate a short tweet announcing a goal in an ice hockey match. The tweet should include the scorer's name, assists, and the time of the goal, without hashtags or emojis."


url = "https://s3-eu-west-1.amazonaws.com/nihl.hokejovyzapis.cz/matches/44/period-events.json"
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()

    # Function to convert seconds to mm:ss
    def format_time(seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"  # Ensures seconds are always two digits

    # Function to get the most recent goal
    def get_most_recent_goal(data):
        most_recent_goal = None

        # Iterate over all keys in the data
        for key in data:
            # Check if the value is a list (period events)
            if isinstance(data[key], list):
                for event in data[key]:
                    # Check if the event is a goal
                    if event.get('type') == 'goal':
                        # Check if 'time' is present at the top level of the event
                        if 'time' in event:
                            # Determine if this is the most recent goal
                            if not most_recent_goal or event['time'] > most_recent_goal['time']:
                                most_recent_goal = event

        return most_recent_goal

    # Fetch the most recent goal
    recent_goal = get_most_recent_goal(data)

    # Prepare the output in JSON format
    if recent_goal:
        goal_info = {
            'goal_scorer': f"{recent_goal['data']['scorer']['name']} {recent_goal['data']['scorer']['surname']}",
            'assistants': [f"{assistant['name']} {assistant['surname']}" for assistant in recent_goal['data']['assistants']],
            'type': recent_goal['type'],
            'time': format_time(recent_goal['time']),  # Convert time to mm:ss
            'powerplay': recent_goal['data'].get('balance', None)
        }
        goal_info_json = json.dumps(goal_info, indent=4)  # Store as a JSON string
        promptWithData = prompt + " " + goal_info_json
        print(goal_info_json)  # Print the JSON string
    else:
        print("No goals found.")
else:
    print(f"Failed to fetch data: {response.status_code}")


gptResponse = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": promptWithData},
    ]
)





#print(response)

from requests_oauthlib import OAuth1Session
import os
import json


consumer_key = "0OezBXeb8hGSqsM3q8RFa2bGT"

# Be sure to add replace the text of the with the text you wish to Tweet. You can also add parameters to post polls, quote Tweets, Tweet with reply settings, and Tweet to Super Followers in addition to other features.
payload = {"text": gptResponse}

# Get request token
request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)

try:
    fetch_response = oauth.fetch_request_token(request_token_url)
except ValueError:
    print(
        "There may have been an issue with the consumer_key or consumer_secret you entered."
    )

resource_owner_key = fetch_response.get("oauth_token")
resource_owner_secret = fetch_response.get("oauth_token_secret")
print("Got OAuth token: %s" % resource_owner_key)

# Get authorization
base_authorization_url = "https://api.twitter.com/oauth/authorize"
authorization_url = oauth.authorization_url(base_authorization_url)
print("Please go here and authorize: %s" % authorization_url)
verifier = input("Paste the PIN here: ")

# Get the access token
access_token_url = "https://api.twitter.com/oauth/access_token"
oauth = OAuth1Session(
    consumer_key,
    client_secret=consumer_secret,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier,
)
oauth_tokens = oauth.fetch_access_token(access_token_url)

access_token = oauth_tokens["oauth_token"]
access_token_secret = oauth_tokens["oauth_token_secret"]

# Make the request
oauth = OAuth1Session(
    consumer_key,
    client_secret=consumer_secret,
    resource_owner_key=access_token,
    resource_owner_secret=access_token_secret,
)

# Making the request
response = oauth.post(
    "https://api.twitter.com/2/tweets",
    json=payload,
)

if response.status_code != 201:
    raise Exception(
        "Request returned an error: {} {}".format(response.status_code, response.text)
    )

print("Response code: {}".format(response.status_code))

# Saving the response as JSON
json_response = response.json()
print(json.dumps(json_response, indent=4, sort_keys=True))