from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import pandas as pd
from SP_Connect import get_site_id, get_timesheet_data, get_timesheet_data_batch
from crew_ai_agent_v1 import analyze_timesheet_data
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

num_items = os.getenv("NUM_ITEMS", "full")
use_batch = os.getenv("USE_BATCH", "False").lower() in ("true", "1", "t")
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000","http://localhost:5173/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    question: str

# Global variable to store the DataFrame
df = None

@app.on_event("startup")
async def startup_event():
    global df
    # Fetch data from SharePoint
    hostname = "maargasystems007.sharepoint.com"
    site_path = "TimesheetSolution"
    list_id = "18391f05-dbb0-4add-bcf2-aa4b637f76f3"  # Timesheet List ID
    site_id = get_site_id(hostname, site_path)
    
    if not site_id:
        raise HTTPException(status_code=500, detail="Failed to get site ID")
    
    df = get_timesheet_data(site_id, list_id)
    
    if df is None or df.empty:
        raise HTTPException(status_code=500, detail="Failed to fetch timesheet data or data is empty")

@app.post("/timesheetanalyze")
async def timesheet_analyze(question: Question) -> Dict[str, Any]:
    try:
        global df
        if df is None or df.empty:
            raise HTTPException(status_code=500, detail="Timesheet data is not loaded or is empty")
        
        # Fetch the specified number of items if not "full"
        if num_items != "full" or use_batch:
            hostname = "maargasystems007.sharepoint.com"
            site_path = "TimesheetSolution"
            list_id = "18391f05-dbb0-4add-bcf2-aa4b637f76f3"  # Timesheet List ID
            site_id = get_site_id(hostname, site_path)
            
            if not site_id:
                raise HTTPException(status_code=500, detail="Failed to get site ID")
            
            if use_batch:
                df = get_timesheet_data_batch(site_id, list_id)
            else:
                df = get_timesheet_data(site_id, list_id)
            
            if df is None or df.empty:
                raise HTTPException(status_code=500, detail="Failed to fetch timesheet data or data is empty")
        
        # Analyze the data using Crew AI
        print("Analyzing timesheet data...")
        analysis_result = analyze_timesheet_data(df, question.question)
        
        return {"result": analysis_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)