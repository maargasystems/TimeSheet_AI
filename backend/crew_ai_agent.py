import pandas as pd
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Create Crew AI Agents
data_analyst = Agent(
    role='Data Analyst',
    goal='Analyze timesheet data and provide comprehensive insights',
    backstory="""You are an expert data analyst specializing in timesheet analysis.
    Your goal is to provide valuable insights about employee workload, project distribution,
    and time management patterns.""",
    verbose=True,
    allow_delegation=False
)

report_writer = Agent(
    role='Report Writer',
    goal='Create clear and concise reports from data analysis',
    backstory="""You are a professional report writer who excels at presenting data insights
    in a clear, structured, and actionable format. You focus on highlighting key findings
    and making recommendations.""",
    verbose=True,
    allow_delegation=False
)

project_analyst = Agent(
    role='Project Analyst',
    goal='Analyze specific project timesheet data and provide detailed project insights',
    backstory="""You are a specialized project analyst who excels at analyzing project-specific timesheet data.
    Your expertise lies in identifying project patterns, resource utilization, and providing actionable project insights.""",
    verbose=True,
    allow_delegation=False
)

employee_analyst = Agent(
    role='Employee Analyst',
    goal='Analyze employee-specific timesheet data and provide detailed workload insights',
    backstory="""You are a specialized employee workload analyst who excels at analyzing individual employee performance and workload.
    Your expertise lies in identifying work patterns, time allocation, and providing insights about employee utilization.""",
    verbose=True,
    allow_delegation=False
)

decision_agent = Agent(
    role='Decision Coordinator',
    goal='Coordinate analysis based on query type and delegate to appropriate specialists',
    backstory="""You are an intelligent coordinator who analyzes requests and determines the most appropriate type of analysis needed.
    You excel at understanding context and delegating tasks to specialized analysts for optimal insights.""",
    verbose=True,
    allow_delegation=True
)

def create_employee_analysis_task(df: pd.DataFrame, employee_id: str) -> Task:
    return Task(
        description=f"""Analyze the timesheet data for employee '{employee_id}':
        {df.to_string()}
        
        Focus on:
        1. Total hours worked this month
        2. Project distribution
        3. Daily/Weekly work patterns
        4. Workload balance
        5. Peak activity periods
        6. Project involvement and contributions""",
        expected_output="""A detailed employee analysis report containing:
        - Total work hours
        - Project allocation breakdown
        - Work patterns and trends
        - Workload distribution
        - Key observations and recommendations
        - Potential areas for optimization""",
        agent=employee_analyst
    )

def create_project_analysis_task(df: pd.DataFrame, project_name: str) -> Task:
    return Task(
        description=f"""Analyze the timesheet data for project '{project_name}':
        {df.to_string()}
        
        Focus on:
        1. Total hours spent on this project this month
        2. Employee contribution distribution
        3. Daily/Weekly effort patterns
        4. Resource utilization trends
        5. Peak activity periods""",
        expected_output="""A detailed project analysis report containing:
        - Project hours summary
        - Resource allocation breakdown
        - Temporal effort patterns
        - Resource utilization metrics
        - Key observations and recommendations""",
        agent=project_analyst
    )

def create_general_analysis_task(df: pd.DataFrame) -> Task:
    return Task(
        description=f"""Analyze the following timesheet data and identify key patterns:
        {df.to_string()}
        
        Focus on:
        1. Total hours spent this month
        2. Employee-wise workload distribution
        3. Daily trends in hours logged
        4. Project-wise time allocation""",
        expected_output="""A detailed analysis report containing:
        - Total hours calculation
        - Employee workload breakdown
        - Daily trend analysis
        - Project distribution metrics
        - Identified patterns and anomalies""",
        agent=data_analyst
    )

def create_report_task() -> Task:
    return Task(
        description="""Based on the analysis, create a comprehensive report in JSON format that includes:
        1. Summary of key findings
        2. Detailed breakdown of workload distribution
        3. Recommendations for workload optimization
        4. Notable patterns or concerns
        
        The output MUST be a valid JSON string with the following structure:
        {
            "summary": {
                "key_findings": ["finding1", "finding2", ...],
                "total_hours": number,
                "total_employees": number
            },
            "workload_distribution": {
                "by_employee": [
                    {"employee": "name", "hours": number, "projects": number}
                ],
                "by_project": [
                    {"project": "name", "hours": number, "employees": number}
                ]
            },
            "recommendations": [
                {"title": "string", "description": "string", "priority": "HIGH|MEDIUM|LOW"}
            ],
            "patterns_and_concerns": [
                {"type": "pattern|concern", "description": "string", "impact": "string"}
            ]
        }""",
        expected_output="""A JSON string containing:
        - Executive summary with key findings
        - Workload distribution metrics
        - Prioritized recommendations
        - Identified patterns and concerns
        
        The output must be valid JSON and follow the specified structure.""",
        agent=report_writer
    )

def analyze_timesheet_data(df: pd.DataFrame, question: str):
    # Clean column names
    df.columns = [col.replace('[', '').replace(']', '') for col in df.columns]
    
    # Print column names for debugging
    print("DataFrame columns:", df.columns)
    
    # Create decision task
    decision_task = Task(
        description=f"""Analyze the following request and determine the appropriate analysis type:
        Question: {question}
        
        Available Analysis Types:
        1. Project Analysis
        2. Employee Analysis
        3. General Analysis
        
        Data Summary:
        {df.describe().to_string()}
        
        Determine the most appropriate analysis type and provide reasoning.""",
        expected_output="""A decision object containing:
        - Selected analysis type
        - Reasoning for selection
        - Recommended focus areas""",
        agent=decision_agent
    )

    # Initialize task list
    tasks = [decision_task]
    
    # Add specific analysis tasks based on parameters
    if "project" in question.lower():
        project_name = question.split("project")[-1].strip()
        if 'ProjectName' in df.columns:
            project_df = df[df['ProjectName'] == project_name].copy()
            if not project_df.empty:
                tasks.append(create_project_analysis_task(project_df, project_name))
        else:
            print("Error: 'ProjectName' column not found in DataFrame")
    
    if "employee" in question.lower():
        employee_id = question.split("employee")[-1].strip()
        if 'EmployeeNameStringId' in df.columns:
            employee_df = df[df['EmployeeNameStringId'] == employee_id].copy()
            if not employee_df.empty:
                tasks.append(create_employee_analysis_task(employee_df, employee_id))
        else:
            print("Error: 'EmployeeNameStringId' column not found in DataFrame")
    
    # Add general analysis task if no specific analysis is requested
    if "project" not in question.lower() and "employee" not in question.lower():
        tasks.append(create_general_analysis_task(df))
    
    # Always add report task as the final task
    tasks.append(create_report_task())

    # Create and run the crew with all agents
    crew = Crew(
        agents=[decision_agent, data_analyst, project_analyst, employee_analyst, report_writer],
        tasks=tasks,
        verbose=True,
        process=Process.sequential
    )

    result = crew.kickoff()
    return result