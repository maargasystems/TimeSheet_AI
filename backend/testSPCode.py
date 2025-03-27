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

def get_site_id():
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
    """Fetch timesheet data from the specified SharePoint list."""
    token = get_access_token()
    
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields($select={select_query})"
    print("Endpoint:", endpoint)
    if num_items != "full":
        endpoint += f"&$top={num_items}"
    else:
        endpoint += f"&$top=9999"
    
    print("Fetching timesheet data...")
    items = []
    
    while endpoint:
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            items.extend(data.get('value', []))
            endpoint = data.get('@odata.nextLink', None)  # Handle pagination
        else:
            print(f"Error fetching timesheet data: {response.status_code}")
            print(f"Error message: {response.text}")
            return None
    
    # Extract the 'fields' dictionary from each item
    fields_data = [item['fields'] for item in items]
    
    df = pd.DataFrame(fields_data)

    # Clean up DataFrame
    df.drop(columns=["@odata.etag", "StartOfTheMonth", "EndOfTheMonth", "Created"], inplace=True, errors='ignore')
    
    # Change date format for "Modified" and "Date" columns
    df["Modified"] = pd.to_datetime(df["Modified"], errors='coerce').dt.strftime('%d/%m/%Y')
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.strftime('%d/%m/%Y')
    
    print("Data fetched successfully")
    print("Number of records:", len(df))
    print("Columns in DataFrame:", df.columns.tolist())
    return df

def main():
    site_id = get_site_id()
    if site_id:
        list_id = "18391f05-dbb0-4add-bcf2-aa4b637f76f3"  # Timesheet List ID
        df = get_timesheet_data(site_id, list_id)
        if df is not None:
            # Filter for year 2025
            # df['Year'] = pd.to_datetime(df['Year'], errors='coerce')  # Ensure 'Year' is in datetime format
            filtered_df = df[df['Year'] == '2025']  # Filter for the year 2025
            
            # Print the first 5 records of the filtered DataFrame
            print("Filtered Data for Year 2025:")
            print(filtered_df.head(5))

if __name__ == "__main__":
    main()