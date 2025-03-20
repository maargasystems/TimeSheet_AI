import requests
import msal
import pandas as pd
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

hostname = "maargasystems007.sharepoint.com"
site_path = "TimesheetSolution"
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
tenant_id = os.getenv("TENANT_ID")
num_items = os.getenv("NUM_ITEMS", "full")

def get_access_token():
    """Obtain an access token for Microsoft Graph API"""
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    app = msal.ConfidentialClientApplication(
        client_id, authority=authority,
        client_credential=client_secret
    )
    
    scopes = ["https://graph.microsoft.com/.default"]
    result = app.acquire_token_for_client(scopes=scopes)
    
    if "access_token" in result:
        return result["access_token"]
    else:
        print(f"Error acquiring token: {result.get('error')}")
        print(f"Error description: {result.get('error_description')}")
        return None

def get_site_id(hostname, site_path):
    token = get_access_token()
    
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    site_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_path}"
    site_response = requests.get(site_url, headers=headers)
    
    if site_response.status_code == 200:
        site_id = site_response.json()["id"]
        print("Site ID:", site_id)
        return site_id
    else:
        print(f"Error getting site ID: {site_response.status_code}")
        print(f"Error message: {site_response.text}")
        return None

def get_timesheet_data(site_id, list_id):
    token = get_access_token()
    
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("Site ID:", site_id)
    endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields"
    if num_items != "full":
        endpoint += f"&$top={num_items}"
    else:
        endpoint += f"&$top=9999"
    print("Fetching timesheet data...")
    print("Endpoint:", endpoint)
    items = []
    while endpoint:
        print("Start while loop")
        response = requests.get(endpoint, headers=headers)
        
        print("Response Status Code:", response.status_code)
        if response.status_code == 200:
            print("Response", response)
            data = response.json()
            # print("Data", data)
            items.extend(data.get('value', []))
            if num_items != "full" and len(items) >= int(num_items):
                items = items[:int(num_items)]
                break
            endpoint = data.get('@odata.nextLink', None)  # Handle pagination
            print(f"Fetched {len(items)} items so far...")
        else:
            print(f"Error fetching timesheet data: {response.status_code}")
            print(f"Error message: {response.text}")
            return None
    
    df = pd.DataFrame(items)
    print("Data fetched successfully")
    print("Number of records:", len(df))
    return df

def get_timesheet_data_batch(site_id, list_id):
    token = get_access_token()
    
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("Site ID:", site_id)
    endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields"
    if num_items != "full":
        endpoint += f"&$top={num_items}"
    else:
        endpoint += f"&$top=9999"
    print("Fetching timesheet data using batch method...")
    print("Endpoint:", endpoint)
    items = []
    batch_size = 20  # Number of requests per batch
    while endpoint:
        print("Start while loop")
        batch_requests = []
        for _ in range(batch_size):
            batch_requests.append({
                "id": str(len(batch_requests) + 1),
                "method": "GET",
                "url": endpoint
            })
            response = requests.post("https://graph.microsoft.com/v1.0/$batch", headers=headers, json={"requests": batch_requests})
            print("Response Status Code:", response.status_code)
            if response.status_code == 200:
                batch_responses = response.json()["responses"]
                for batch_response in batch_responses:
                    if batch_response["status"] == 200:
                        data = batch_response["body"]
                        items.extend(data.get('value', []))
                        if num_items != "full" and len(items) >= int(num_items):
                            items = items[:int(num_items)]
                            break
                        endpoint = data.get('@odata.nextLink', None)  # Handle pagination
                        print(f"Fetched {len(items)} items so far...")
                    else:
                        print(f"Error in batch response: {batch_response['status']}")
                        print(f"Error message: {batch_response['body']}")
                        return None
            else:
                print(f"Error fetching timesheet data: {response.status_code}")
                print(f"Error message: {response.text}")
                return None
    
    df = pd.DataFrame(items)
    print("Data fetched successfully using batch method")
    print("Number of records:", len(df))
    return df