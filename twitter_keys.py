import requests
from requests_oauthlib import OAuth1Session
import os

# Set your credentials (API Key and API Key Secret)
CONSUMER_KEY = "0OezBXeb8hGSqsM3q8RFa2bGT"
CONSUMER_SECRET = "SzxuWOzuP4i7mCUC9GZIddPUpi8rZjWI1kAQ0v136NLNNOs5zT"

# Step 1: Obtain a request token
request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
oauth = OAuth1Session(CONSUMER_KEY, client_secret=CONSUMER_SECRET)

try:
    fetch_response = oauth.fetch_request_token(request_token_url)
except ValueError as e:
    print(f"Error fetching request token: {e}")
    exit(1)

resource_owner_key = fetch_response.get('oauth_token')
resource_owner_secret = fetch_response.get('oauth_token_secret')

# Step 2: Redirect user to Twitter to authorize
base_authorization_url = "https://api.twitter.com/oauth/authorize"
authorization_url = oauth.authorization_url(base_authorization_url)
print(f"Go to the following URL to authorize your app: {authorization_url}")

# Step 3: After authorizing, Twitter will provide a PIN code (oauth_verifier)
oauth_verifier = input('Paste the PIN code (oauth_verifier) here: ')

# Step 4: Get an access token
access_token_url = "https://api.twitter.com/oauth/access_token"
oauth = OAuth1Session(
    CONSUMER_KEY,
    client_secret=CONSUMER_SECRET,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=oauth_verifier
)

try:
    oauth_tokens = oauth.fetch_access_token(access_token_url)
except ValueError as e:
    print(f"Error fetching access token: {e}")
    exit(1)

access_token = oauth_tokens.get('oauth_token')
access_token_secret = oauth_tokens.get('oauth_token_secret')

print(f"Access Token: {access_token}")
print(f"Access Token Secret: {access_token_secret}")

# Save the tokens securely for future use
