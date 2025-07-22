import msal
import requests
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")


# --- Endpoints ---
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPE = ['https://graph.microsoft.com/.default']
USERS_ENDPOINT = 'https://graph.microsoft.com/v1.0/users'

# --- Authentication ---
app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)

print("🔐 Requesting token...")
token_response = app.acquire_token_for_client(scopes=SCOPE)

if "access_token" in token_response:
    print("✅ Token acquired successfully.")

    headers = {'Authorization': 'Bearer ' + token_response['access_token']}
    users_response = requests.get(USERS_ENDPOINT, headers=headers)

    print("📦 Users API Status Code:", users_response.status_code)

    if users_response.status_code != 200:
        print("❌ Failed to fetch users:", users_response.text)
    else:
        users = users_response.json().get('value', [])
        print(f"👥 Total users retrieved: {len(users)}")

        for user in users:
            user_id = user['id']
            username = user.get('userPrincipalName', 'N/A')

            mfa_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/authentication/methods"
            mfa_response = requests.get(mfa_endpoint, headers=headers)

            if mfa_response.status_code == 200:
                mfa_methods = mfa_response.json().get('value', [])
                print({
                    "user": username,
                    "mfa_enabled": len(mfa_methods) > 0
                })
            else:
                print(f"⚠️ Could not retrieve MFA methods for {username}: {mfa_response.status_code}")
else:
    print("❌ Failed to acquire token.")
    print("Response type:", type(token_response))
    print("Raw token response:", token_response)
