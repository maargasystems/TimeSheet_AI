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

filter_agent = Agent(
    role='Filter Agent',
    goal='Write and execute the filter condition to filter the data from the DataFrame based on the user question',
    backstory="""You are an expert in data filtering. 
    Your task is to understand the user's question and 
    return the appropriate Python filter code as a single string 
    without any additional comments or explanations, In addition initialize the filter query in variable "filtered_data". 
    For example, return: 
    filtered_data = df[df['ProjectName'].str.contains('McKinsey_LN Support_2', case=False, na=False)]""",
    verbose=True,
    allow_delegation=False
)

def chunk_text(text: str, max_length: int = 120000) -> list:
    """Chunk the text into smaller parts to avoid exceeding the maximum length."""
    chunks = []
    while len(text) > max_length:
        chunk = text[:max_length]
        last_space = chunk.rfind(' ')
        if last_space != -1:
            chunk = chunk[:last_space]
        chunks.append(chunk)
        text = text[len(chunk):]
    chunks.append(text)
    return chunks

def create_filter_task(df: pd.DataFrame, question: str) -> list:
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []
    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Write and execute the filter condition to filter the data from the DataFrame based on the user question:
            Question: {question}
            
            DataFrame columns: {df.columns.tolist()}
            
            DataFrame chunk:
            {chunk}
            
            The filter condition should be written in Python and returned as a query string.""",
            expected_output="""A Python filter query string that can be applied to the DataFrame to retrieve the relevant data.""",
            agent=filter_agent
        ))
    return tasks

def create_employee_analysis_task(df: pd.DataFrame, employee_id: str) -> list:
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []
    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Analyze the timesheet data for employee '{employee_id}':
            {chunk}
            
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
        ))
    return tasks

def create_project_analysis_task(df: pd.DataFrame, project_name: str) -> list:
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []
    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Analyze the timesheet data for project '{project_name}':
            {chunk}
            
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
        ))
    return tasks

def create_general_analysis_task(df: pd.DataFrame) -> list:
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []
    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Analyze the following timesheet data and identify key patterns:
            {chunk}
            
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
        ))
    return tasks

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

def filter_dataframe(df, filter_code):
    # Debug: Initial DataFrame - Print only the ProjectName column
    print("Initial DataFrame (ProjectName column):\n", df['ProjectName'])

    # Prepare a local context for the exec call
    local_context = {'df': df}  # Include df in local context
    filter_code_str = str(filter_code)
    # Execute the filter code dynamically
    exec(filter_code_str, {}, local_context)  # Pass empty globals, local_context captures the variables
    print("Executed filter code.")

    # Retrieve filtered_data from local_context (it should be defined in filter_code)
    filtered_data = local_context.get('filtered_data', None)

    # Debugging: Print the filter result
    if filtered_data is not None:
        print("Filter result:\n", filtered_data)
    else:
        print("No filtered data returned.")

    # Return the filtered DataFrame, if any
    return filtered_data if filtered_data is not None else pd.DataFrame()

def analyze_timesheet_data(df: pd.DataFrame, question: str):
    # Clean column names
    df.columns = [col.replace('[', '').replace(']', '') for col in df.columns]
    
    # Print column names for debugging
    print("DataFrame columns:", df.columns)
    
    # Create filter tasks
    filter_tasks = create_filter_task(df, question)
    
    # Run the filter tasks to get the filter query
    crew = Crew(
        agents=[filter_agent],
        tasks=filter_tasks,
        verbose=True,
        process=Process.sequential
    )
    filter_result = crew.kickoff()
    
    # Debugging: Print filter result
    print("Filter result:", filter_result)
    
    
    # Extract the filter query from the result
    # if 'output' in filter_result:
    #     filter_query = filter_result['output']
    # else:
    #     print("Key 'output' not found in CrewOutput.")
    #     print("CrewOutput keys:", filter_result.keys())
    #     print("CrewOutput content:", filter_result)
    #     return None
    filtered_df = filter_dataframe(df, filter_result)

# Print the filtered DataFrame outside
    print("Filtered DataFrame:\n", filtered_df)
       
    # Print the filtered DataFrame
    print("Filtered DataFrame:", filtered_df)
    
    # Create decision task
    decision_task = Task(
        description=f"""Analyze the following request and determine the appropriate analysis type:
        Question: {question}
        
        Available Analysis Types:
        1. Project Analysis
        2. Employee Analysis
        3. General Analysis
        
        Data Summary:
        {filtered_df.describe().to_string()}
        
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
        if 'ProjectName' in filtered_df.columns:
            project_df = filtered_df[filtered_df['ProjectName'] == project_name].copy()
            if not project_df.empty:
                tasks.extend(create_project_analysis_task(project_df, project_name))
        else:
            print("Error: 'ProjectName' column not found in DataFrame")
    
    if "employee" in question.lower():
        employee_id = question.split("employee")[-1].strip()
        if 'EmployeeNameStringId' in filtered_df.columns:
            employee_df = filtered_df[filtered_df['EmployeeNameStringId'] == employee_id].copy()
            if not employee_df.empty:
                tasks.extend(create_employee_analysis_task(employee_df, employee_id))
        else:
            print("Error: 'EmployeeNameStringId' column not found in DataFrame")
    
    # Add general analysis task if no specific analysis is requested
    if "project" not in question.lower() and "employee" not in question.lower():
        tasks.extend(create_general_analysis_task(filtered_df))
    
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