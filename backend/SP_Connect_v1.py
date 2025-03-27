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

columns_to_select = [
    "Title", "Modified", "Created", "EmployeeName", "Date", "ProjectName", "SOWCode",
    "Module", "Sprint", "TaskOrUserStory", "SubTask", "ActualTimeSpent", "Remarks",
    "Year", "Manager", "SOWCodeSample"
]
select_query = ",".join(columns_to_select)

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

def get_timesheet_data_with_filter(site_id, list_id, filter_query):
    token = get_access_token()
    
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("Site ID:", site_id)
    endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields($select={select_query}){filter_query} and fields/Date gt '2024-12-31T23:59:59Z'&$orderby=fields/EmployeeName,fields/Date"
    # endpoint=f"https://graph.microsoft.com/v1.0/sites/maargasystems007.sharepoint.com,9e4a3d83-aa87-4691-89f7-6f0c802225fe,967db760-c140-42d6-b4a4-dc7c21266cac/lists/18391f05-dbb0-4add-bcf2-aa4b637f76f3/items?expand=fields($select=Title,Modified,Created,EmployeeName,Date,ProjectName,SOWCode,Module,Sprint,TaskOrUserStory,SubTask,ActualTimeSpent,Remarks,Year,Manager,SOWCodeSample)&$filter=fields/Date gt '2024-12-31T23:59:59Z'&$orderby=fields/EmployeeName"
    print("endpoint:", endpoint)
    if num_items != "full":
        endpoint += f"&$top={num_items}"
    else:
        endpoint += f"&$top=9999"
    print("Fetching timesheet data with filter...")
    print("Endpoint:", endpoint)
    
    log_file = "filtered_data_log.txt"
    with open(log_file, "a") as f:
        f.write(f"Endpoint: {endpoint}\n")
        
    items = []
    while endpoint:
        print("Start while loop")
        response = requests.get(endpoint, headers=headers)
        
        print("Response Status Code:", response.status_code)
        if response.status_code == 200:
            print("Response", response)
            data = response.json()
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
    
    # Extract the 'fields' dictionary from each item
    fields_data = [item['fields'] for item in items]
    
    df = pd.DataFrame(fields_data)
    
    # Remove specified columns
    df.drop(columns=["@odata.etag", "StartOfTheMonth", "EndOfTheMonth", "Created","Modified","Year","SOWCodeSample","Manager","Remarks","TaskorUserStory","Module","SOWCode"], inplace=True, errors='ignore')
    
    # Change date format for "Modified" and "Date" columns
    # df["Modified"] = pd.to_datetime(df["Modified"]).dt.strftime('%d/%m/%Y')
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime('%d/%m/%Y')
    
    print("Data fetched successfully with filter")
    print("Number of records:", len(df))
    print("Columns in DataFrame:", df.columns.tolist())
    return df