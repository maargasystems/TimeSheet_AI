from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import pandas as pd
from SP_Connect_v1 import get_timesheet_data_with_filter, get_site_id
from crew_ai_agent_v1 import analyze_timesheet_data
from crewai import Agent, Task, Crew, Process
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

num_items = os.getenv("NUM_ITEMS", "full")
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000", # If you have a local FastAPI server running here
        "http://localhost:3000",  # If you have something running on this port
        "http://localhost:5173"   # Vite development server
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Limit to only required HTTP methods
    allow_headers=["*"],
)

class Question(BaseModel):
    question: str

# Global variable to store the DataFrame
df = None

graph_api_filter_agent = Agent(
    role='Graph API Filter Agent',
    goal='Generate Graph API filter queries based on user requests and log the queries',
    backstory="""You are an expert in building Graph API filter queries. 
    Your task is to analyze the user request and return a valid Graph API filter query string.
    Ensure that all necessary parameters are included and the query is well-formed for execution.""",
    verbose=True,
    allow_delegation=False
)

def create_graph_api_filter_task(question: str) -> Task:
    """Create a task for generating a Graph API filter query based on the user's question."""
    return Task(
        description=f"""Analyze the following question and generate a suitable Graph API filter query:
        Question: {question}
        
        Notes:
        - Focus on generating a valid and executable Graph API filter query.
        - Parameters should be included as necessary for filtering data.
        - Example of a Graph API filter query: `&$filter=fields/ProjectName eq 'your_project_name'`. 
        Return only the filter query string without additional comments or explanations or quotes.""",
        expected_output="""A Graph API filter query string that corresponds to the user's question, 
        ready to be executed against a Graph API endpoint.""",
        agent=graph_api_filter_agent
    )

@app.post("/timesheetanalyze")
async def timesheet_analyze(question: Question) -> Dict[str, Any]:
    try:
        global df
        
        # Generate the filter query based on the user's question
        # filter_task = create_graph_api_filter_task(question.question)
        # filter_query = filter_task.run()
        graph_api_filter_task = create_graph_api_filter_task(question)
        
        gapi_crew = Crew(
            agents=[graph_api_filter_agent],
            tasks=[graph_api_filter_task],
            verbose=True,
            process=Process.sequential
        )
        
        gapi_crew.kickoff()
        graph_api_query = graph_api_filter_task.output
        log_file = "filtered_data_log.txt"
        with open(log_file, "a") as f:
            f.write(f"\n\nQuestion: {question}\n")
            f.write(f"\n**Graph API Filter Agent**\n")
            f.write(f"Graph API Query: {graph_api_query}\n")
        print("Generated filter query:", graph_api_query)
        
        # Fetch the specified number of items if not "full"
        hostname = "maargasystems007.sharepoint.com"
        site_path = "TimesheetSolution"
        list_id = "18391f05-dbb0-4add-bcf2-aa4b637f76f3"  # Timesheet List ID
        site_id = get_site_id(hostname, site_path)
        print("Site ID:", site_id)
        if not site_id:
            raise HTTPException(status_code=500, detail="Failed to get site ID")
        
        df = get_timesheet_data_with_filter(site_id, list_id, graph_api_query)
        
        if df is None or df.empty:
            raise HTTPException(status_code=500, detail="Failed to fetch timesheet data or data is empty")
        
        log_file = "filtered_data_log.txt"
        with open(log_file, "a") as f:
            f.write(f"\n\nRetrieved Data:\n")
            f.write(f"Number of records: {len(df)}\n")
            f.write(f"Columns in DataFrame: {df.columns.tolist()}\n")
            f.write(df.to_string())
        # Analyze the data using Crew AI
        print("Analyzing timesheet data...")
        analysis_result = analyze_timesheet_data(df, question.question)
        
        return {"result": analysis_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)