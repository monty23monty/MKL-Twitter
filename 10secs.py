import json
import requests
import openai
import time
from requests_oauthlib import OAuth1Session

# ===========================
# Configuration and Constants
# ===========================

GAME_ID = "44"

# OpenAI API Key (It's safer to load this from environment variables)

# OpenAI Model
OPENAI_MODEL = "gpt-4o-mini"  # Update to the correct model name if necessary

# OpenAI Prompt Template
OPENAI_PROMPT_TEMPLATE = (
    "Generate a short tweet announcing a goal in an ice hockey match. "
    "The tweet should include the scorer's name, assists, the time of the goal, "
    "and the scoreline at either the start or end of the tweet, without hashtags or emojis."
)

# Twitter API Credentials (Replace with your actual credentials or load from environment variables)
CONSUMER_KEY = "0OezBXeb8hGSqsM3q8RFa2bGT"

ACCESS_TOKEN = "1836467381037596673-8LQx4zK551HwIa8oHPzCTDhyWj7672"


# URLs
MATCH_EVENTS_URL = f"https://s3-eu-west-1.amazonaws.com/nihl.hokejovyzapis.cz/matches/{GAME_ID}/period-events.json"
TWITTER_TWEET_URL = "https://api.twitter.com/2/tweets"

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# ===========================
# Helper Functions
# ===========================

def format_time(seconds):
    """Convert seconds to mm:ss format."""
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"


def get_all_goals(data):
    """Extract all goal events from the match data."""
    all_goals = []

    for period, events in data.items():
        if isinstance(events, list):
            for event in events:
                if event.get('type') == 'goal' and 'time' in event:
                    goal_info = {
                        'event_id': event.get('data', {}).get('id'),
                        'goal_scorer': f"{event['data']['scorer']['name']} {event['data']['scorer']['surname']}",
                        'assistants': [
                            f"{assistant['name']} {assistant['surname']}" for assistant in event['data'].get('assistants', [])
                        ],
                        'time': format_time(event['time']),
                        'powerplay': event['data'].get('balance', None),
                        'team': event['data'].get('team', 'Unknown Team')  # Updated line
                    }
                    all_goals.append(goal_info)

    print("Goal Info: ")
    for goal in all_goals:
        print(goal)
    return all_goals



def fetch_match_data(url):
    """Fetch match event data from the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching match data: {e}")
        return None


def fetch_fixture_data(fixtures_url, game_id):
    """Fetch fixture data to get home and guest team names."""
    try:
        response = requests.get(fixtures_url)
        response.raise_for_status()
        data = response.json()
        for match in data['matches']:
            if match['id'] == int(game_id):
                return match['home']['name'], match['guest']['name']
    except requests.RequestException as e:
        print(f"Error fetching fixture data: {e}")
    return None, None

def generate_tweet(all_goals, home_team, guest_team):
    """Generate a tweet using OpenAI's GPT model based on the goal information."""

    # Check if any goals have been scored
    if not all_goals:
        print("No goals found to generate a tweet.")
        return None

    # Get the most recent goal
    latest_goal = all_goals[-1]  # The last goal in the list is the most recent one

    # Compute the current scoreline


    # Create a prompt for GPT to generate a tweet for the latest goal with context
    prompt = (
        f"{OPENAI_PROMPT_TEMPLATE}\n\n"
        f"The most recent goal was scored by {latest_goal['goal_scorer']} at {latest_goal['time']} for the {latest_goal['team']} team.\n"
        f"Assistants: {', '.join(latest_goal['assistants']) if latest_goal['assistants'] else 'None'}.\n"
        f"The tweet should be in the format: '[Time] [Current Score] - [Goal Description]', "
        f"or '[Goal Description] [Time] [Current Score]'."
        f"Teams playing: home: {home_team} vs visitor: {guest_team}"
        f"All Goals so far: {all_goals}"
    )
    print(f"Prompt: {prompt}")

    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an assistant helping generate tweets."},
                {"role": "user", "content": prompt},
            ]
        )
        print(f"Response: {response}")

        # Extract the generated tweet
        tweet = response.choices[0].message.content.strip()
        return tweet
    except Exception as e:
        print(f"Error generating tweet: {e}")
        return None

def authenticate_twitter():
    """Authenticate with Twitter using OAuth1 and return an authenticated session."""
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=ACCESS_TOKEN,
        resource_owner_secret=ACCESS_TOKEN_SECRET,
    )
    return oauth


def post_tweet(oauth, tweet_text):
    """Post the tweet to Twitter."""
    payload = {"text": tweet_text}

    try:
        response = oauth.post(TWITTER_TWEET_URL, json=payload)
        response.raise_for_status()
        print("Tweet posted successfully!")
        print(json.dumps(response.json(), indent=4, sort_keys=True))
    except requests.RequestException as e:
        print(f"Error posting tweet: {e}")
        if response is not None:
            print(f"Response: {response.text}")


# ===========================
# Main Execution Flow
# ===========================

def main():
    # Authenticate with Twitter once
    twitter_oauth = authenticate_twitter()
    if not twitter_oauth:
        return

    last_goal_id = None  # We can use the event_id of the last goal

    # Fetch home and guest team names using the fixture data
    fixtures_url = "https://s3-eu-west-1.amazonaws.com/nihl.hokejovyzapis.cz/league-matches/2024/1.json"
    home_team, guest_team = fetch_fixture_data(fixtures_url, GAME_ID)

    if not home_team or not guest_team:
        print(f"Could not retrieve team names for game {GAME_ID}")
        return

    while True:
        # Step 1: Fetch match data
        data = fetch_match_data(MATCH_EVENTS_URL)
        if not data:
            time.sleep(10)
            continue

        # Step 2: Get all goals
        all_goals = get_all_goals(data)
        if not all_goals:
            print("No goals found.")
        else:
            # Check if there is a new goal
            latest_goal = all_goals[-1]
            latest_goal_id_in_data = latest_goal['event_id']

            if last_goal_id != latest_goal_id_in_data:
                # New goal detected
                # Step 3: Generate tweet using OpenAI, passing the home and guest teams
                tweet = generate_tweet(all_goals, home_team, guest_team)
                if tweet:
                    print(f"Generated Tweet: {tweet}")
                    # Step 5: Post the tweet
                    post_tweet(twitter_oauth, tweet)
                last_goal_id = latest_goal_id_in_data
            else:
                print("No new goals.")

        # Wait 10 seconds before polling again
        time.sleep(10)

if __name__ == "__main__":
    main()
