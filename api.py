import json
import requests
from openai import OpenAI  # Ensure you have the correct OpenAI library installed
from requests_oauthlib import OAuth1Session

# ===========================
# Configuration and Constants
# ===========================

GAME_ID = "44"

# OpenAI API Key (It's safer to load this from environment variables)

# Twitter API Credentials (Replace with your actual credentials or load from environment variables)
CONSUMER_KEY = "0OezBXeb8hGSqsM3q8RFa2bGT"

# URLs
MATCH_EVENTS_URL = "https://s3-eu-west-1.amazonaws.com/nihl.hokejovyzapis.cz/matches/"+ GAME_ID +"/period-events.json"
OPENAI_MODEL = "gpt-4o-mini"  # Update to the correct model name if necessary
OPENAI_PROMPT_TEMPLATE = (
    "Generate a short tweet announcing a goal in an ice hockey match. "
    "The tweet should include the scorer's name, assists, the time of the goal, "
    "and the scoreline at either the start or end of the tweet, without hashtags or emojis."
)

TWITTER_TWEET_URL = "https://api.twitter.com/2/tweets"


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
                        'goal_scorer': f"{event['data']['scorer']['name']} {event['data']['scorer']['surname']}",
                        'assistants': [
                            f"{assistant['name']} {assistant['surname']}" for assistant in event['data'].get('assistants', [])
                        ],
                        'time': format_time(event['time']),
                        'powerplay': event['data'].get('balance', None)
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


def generate_tweet(all_goals):
    """Generate a tweet using OpenAI's GPT model based on the goal information."""
    global gpt_response

    # Check if any goals have been scored
    if not all_goals:
        print("No goals found to generate a tweet.")
        return None

    # Get the most recent goal
    latest_goal = all_goals[-1]  # The last goal in the list is the most recent one


    # Create a prompt for GPT to generate a tweet for the latest goal with context
    prompt = (
        f"{OPENAI_PROMPT_TEMPLATE}\n\n"
        f"The most recent goal was scored by {latest_goal['goal_scorer']} at {latest_goal['time']}.\n"
        f"Here are all the goals scored so far for context (to generate the accurate scoreline):\n"
        f"Total goals: {all_goals}\n"
        f"The tweet format should be: '[latest_goal['time']] [current_score] - [goal_description]' "
        f"or [goal_description] [latest_goal['time']] [current_score]."
    )

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        gpt_response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an assistant helping generate tweets."},
                {"role": "user", "content": prompt},
            ]
        )
        print(f"Response: {gpt_response}")

        # Extract the generated tweet
        tweet = gpt_response.choices[0].message.content.strip()
        return tweet
    except Exception as e:
        print(f"Error generating tweet: {e}")
        return None


def authenticate_twitter():
    """Authenticate with Twitter using OAuth1 and return an authenticated session."""
    request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
    oauth = OAuth1Session(CONSUMER_KEY, client_secret=CONSUMER_SECRET)

    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except ValueError:
        print("There may have been an issue with the consumer_key or consumer_secret you entered.")
        return None

    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    print(f"Got OAuth token: {resource_owner_key}")

    # Get authorization
    base_authorization_url = "https://api.twitter.com/oauth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print(f"Please go here and authorize: {authorization_url}")
    verifier = input("Paste the PIN here: ")

    # Get the access token
    access_token_url = "https://api.twitter.com/oauth/access_token"
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    try:
        oauth_tokens = oauth.fetch_access_token(access_token_url)
    except Exception as e:
        print(f"Error fetching access token: {e}")
        return None

    access_token = oauth_tokens["oauth_token"]
    access_token_secret = oauth_tokens["oauth_token_secret"]

    # Create a new OAuth1Session with the access tokens
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
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
        print(f"Response: {response.text}")


# ===========================
# Main Execution Flow
# ===========================

def main():
    # Step 1: Fetch match data
    data = fetch_match_data(MATCH_EVENTS_URL)
    if not data:
        return

    # Step 2: Get all goals
    all_goals = get_all_goals(data)
    if not all_goals:
        print("No goals found.")
        return

    # Step 3: Generate tweet using OpenAI
    tweet = generate_tweet(all_goals)
    if not tweet:
        return

    print(f"Generated Tweet: {tweet}")

    # Step 4: Authenticate with Twitter
    twitter_oauth = authenticate_twitter()
    if not twitter_oauth:
        return

    # Step 5: Post the tweet
    post_tweet(twitter_oauth, tweet)


if __name__ == "__main__":
    main()
