# integrated_analysis.py

import os
import json
import logging
from datetime import datetime

import pandas as pd
import requests
import msal
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

# ==============================
# 1. Load Environment Variables
# ==============================

load_dotenv()

# Retrieve environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUM_ITEMS = os.getenv("NUM_ITEMS", "full")
SHAREPOINT_LIST_ID = os.getenv("SHAREPOINT_LIST_ID")

# Validate essential environment variables
if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID, OPENAI_API_KEY, SHAREPOINT_LIST_ID]):
    raise ValueError("One or more environment variables are missing. Please check your .env file.")

# ==============================
# 2. Setup Logging
# ==============================

logging.basicConfig(
    filename='application.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================
# 3. Helper Functions
# ==============================

def format_as_html_table(dataframe: pd.DataFrame, title: str) -> str:
    """Convert a pandas DataFrame to an HTML table."""
    html = f"<h3>{title}</h3>"
    html += dataframe.to_html(index=False, border=0, classes='dataframe table table-bordered', justify='center')
    return html

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

# ==============================
# 4. Define Agents
# ==============================

# Existing Agents
data_analyst = Agent(
    role='Data Analyst',
    goal='Analyze timesheet data and provide comprehensive insights',
    backstory="""You are an expert data analyst specializing in timesheet analysis.
    Your goal is to provide valuable insights about employee workload, project distribution,
    and time management patterns. Ensure all calculations are accurate and precise, matching the actual database values.""",
    verbose=True,
    allow_delegation=False
)

report_writer = Agent(
    role='Report Writer',
    goal='Create clear and concise reports from data analysis',
    backstory="""You are a professional report writer who excels at presenting data insights
    in a structured, actionable HTML format. You focus on creating clear tables that highlight key findings
    and making recommendations. Ensure that all reported values are accurate and match the actual database.""",
    verbose=True,
    allow_delegation=False
)

project_analyst = Agent(
    role='Project Analyst',
    goal='Analyze specific project timesheet data and provide detailed insights, ensuring all calculations of hours worked are accurate and precise, while recognizing that outputs may vary based on nuanced interpretations of the data.',
    backstory="""You are a specialized project analyst with a strong emphasis on analyzing project-specific timesheet data. 
    Your expertise lies in identifying project patterns, resource utilization, and delivering actionable insights. 
    It is crucial that all calculations, particularly concerning hours worked, are performed accurately using Decimal for floating-point operations. 
    Ensure that all reported values match the actual database values. Deliver precise and reliable reports that include various interpretations and conclusions from the data to better inform project management decisions.""",
    verbose=True,
    allow_delegation=False
)

employee_analyst = Agent(
    role='Employee Analyst',
    goal='Analyze employee-specific timesheet data and provide detailed workload insights',
    backstory="""You are a specialized employee workload analyst who excels at analyzing individual employee performance and workload.
    Your expertise lies in identifying work patterns, time allocation, and providing insights about employee utilization. Ensure all calculations are accurate and match the actual database values.""",
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

question_analyzer_agent = Agent(
    role='Question Analyzer',
    goal='Analyze the user question to determine if it pertains to a project, an employee, or a specific time-related aspect, and extract the relevant details.',
    backstory="""You are an expert in natural language processing. 
    Your task is to analyze the user's question and determine whether it pertains to a specific project, employee, or a time-related aspect (Year, Month, Day, or Date). 
    You will also extract the relevant project name or employee name from the question, as well as any time-related information if applicable.""",
    verbose=True,
    allow_delegation=False
)

# New Agents
authentication_agent = Agent(
    role='Authentication Agent',
    goal='Authenticate with Microsoft Graph API to obtain access tokens.',
    backstory="""You are responsible for authenticating with Microsoft Graph API.
    Your primary task is to obtain access tokens required for accessing SharePoint data securely.
    Ensure that tokens are acquired efficiently and handle any authentication errors gracefully.""",
    verbose=True,
    allow_delegation=False
)

data_retrieval_agent = Agent(
    role='Data Retrieval Agent',
    goal='Connect to SharePoint via Microsoft Graph API and retrieve timesheet data.',
    backstory="""Your role is to connect to SharePoint using Microsoft Graph API to fetch timesheet data.
    Ensure secure connections, handle pagination, and process the retrieved data accurately.""",
    verbose=True,
    allow_delegation=False
)

# ==============================
# 5. Define Task Creation Functions
# ==============================

def create_authentication_task() -> Task:
    """Create a task for authenticating with Microsoft Graph API."""
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    tenant_id = TENANT_ID

    description = f"""Authenticate with Microsoft Graph API to obtain an access token.
Use the following credentials:
- Client ID: {client_id}
- Client Secret: {client_secret}
- Tenant ID: {tenant_id}

Ensure the token is acquired successfully and handle any errors."""

    expected_output = """A JSON object containing and return only in JSON format don't give reponse in string format:
- access_token: The obtained access token string.
- token_type: The type of the token (e.g., Bearer).
- expires_in: Token expiration time in seconds."""

    return Task(
        description=description,
        expected_output=expected_output,
        agent=authentication_agent
    )

def create_get_site_id_task(hostname: str, site_path: str, access_token: str) -> Task:
    """Create a task to retrieve the SharePoint site ID."""
    
    description = f"""Using the provided access token, retrieve the site ID for the SharePoint site:
- Hostname: {hostname}
- Site Path: {site_path}

Use the following endpoint:
https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_path}

Ensure the site ID is retrieved successfully and handle any errors. The output must be in JSON format."""

    expected_output = """A JSON object containing:
- site_id: The unique identifier of the SharePoint site."""

    return Task(
        description=description,
        expected_output=expected_output,
        agent=data_retrieval_agent
    )
    
def create_retrieve_timesheet_data_task(site_id: str, list_id: str, select_query: str, filter_query: str, num_items: str) -> Task:
    """Create a task to retrieve timesheet data from SharePoint."""
    
    description = f"""Retrieve timesheet data from SharePoint list:
- Site ID: {site_id}
- List ID: {list_id}
- Select Query: {select_query}
- Filter Query: {filter_query}
- Number of Items: {num_items}

Ensure data is fetched accurately, handle pagination, and process the data into a pandas DataFrame."""

    expected_output = """A pandas DataFrame containing the retrieved timesheet data with specified columns."""

    return Task(
        description=description,
        expected_output=expected_output,
        agent=data_retrieval_agent
    )

def create_question_analysis_task(question: str) -> Task:
    """Create a task for analyzing the user question."""
    
    description = f"""Analyze the following question to determine if it pertains to Project Analysis, Employee Analysis, or Time Analysis, and extract the relevant details:
Question: {question}

Available Analysis Types:
1. Project Analysis - Choose this if the question is related to a specific project.
2. Employee Analysis - Choose this if the question is related to a specific employee.
3. Time Analysis - Choose this if the question is related to a specific time period, date, day, month, year or a phrase that related to Calendar.

Please provide:
- The analysis type selected (Project Analysis, Employee Analysis, or Time Analysis).
- The extracted name (project name or employee name, if applicable).
- Any specific time-related information (Year, Month, Day, or Date) if mentioned in the question. Return "Year" if the question pertains to a Year, "Month" for Months, "Day" for Days, or "Date" if it is about a specific Date."""

    expected_output = """A decision object containing the following information in JSON format:
- Selected analysis type (Project Analysis, Employee Analysis, or Time Analysis)
- Extracted name (project name or employee name, if applicable)
- Time-related information (Year, Month, Day, or Date, if specified)"""

    return Task(
        description=description,
        expected_output=expected_output,
        agent=question_analyzer_agent
    )

def create_project_analysis_task(df: pd.DataFrame, project_name: str) -> list:
    """Create tasks for analyzing project-specific timesheet data."""
    
    tasks = []

    tasks.append(Task(
        description=f"""Analyze the timesheet data for project '{project_name}':
{df.to_string()}

Note: 
- Ensure calculations are accurate, especially for summing hours worked.
- Check that 'ActualTimeSpent' has accurate floating-point values.

Focus on:
1. Total hours spent on the project.
2. Monthly hours breakdown.
3. Total hours by each employee.
4. Major tasks performed by employees.
5. Project start date for timesheet entries.
6. Average hours worked per day, week, and month.
7. Employee contribution distribution.
8. Daily and weekly work patterns.
9. Resource utilization trends.
10. Identify peak activity periods.
""",
        expected_output="""A detailed project analysis report with HTML output containing:
- Total hours summary
- Monthly hours breakdown
- Employee hours contributions
- Major tasks performed
- Start date for timesheet entries
- Average hours per day, week, and month
- Resource allocation breakdown
- Work patterns
- Utilization metrics
- Key findings and recommendations
""",
        agent=project_analyst
    ))
    
    # Logging the task
    log_file = "filtered_data_log.txt"    
    with open(log_file, "a") as f:
        f.write(f"\n\n**Project Analysis Agent**\n")
        f.write(f"Project Name: {project_name}\n")
        f.write(f"Tasks: {[task.description for task in tasks]}\n")
        
    return tasks

def create_employee_analysis_task(df: pd.DataFrame, employee_id: str) -> list:
    """Create tasks for analyzing employee-specific timesheet data."""
    
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []

    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Analyze the timesheet data for employee '{employee_id}':

**Data:** {chunk}

**Important Notes:** 
    - All calculations must be precise. Ensure that the 'ActualTimeSpent' column correctly includes floating-point values, as in the following example: 2.0 + 2.5 + 1.5 should equal 6.
    - When grouping employee data by hours, accuracy is crucial. Confirm that hours are summed correctly across different timeframes and tasks to avoid misrepresentation of total work hours.

**Focus Areas:**
1. Calculate the total hours worked overall by the employee with detail to precision.
2. Provide a year-wise breakdown of total hours worked, ensuring correct calculations.
3. Include a month-wise breakdown of total hours worked, verifying each entry is aggregated correctly.
4. Analyze total hours worked on a project-wise basis, accounting for all related tasks.
5. Identify both major and minor tasks the employee has worked on, ensuring clarity on each.
6. Explore daily and weekly work patterns to identify potential anomalies.
7. Assess workload balance across projects to ensure fair distribution of hours.
8. Identify peak activity periods based on timesheet data with accurate grouping.
9. Evaluate resource utilization trends throughout the work period and highlight any discrepancies.
10. Examine the employee's contributions and involvement in various projects, ensuring all entries are accounted for appropriately.
""",
            expected_output="""A comprehensive employee analysis report with HTML output containing:
- Total hours worked in aggregate, with accurate calculations.
- Yearly and monthly breakdown of hours worked, ensuring no discrepancies.
- Time allocations specific to each project, verifying total contributions.
- Insights on major and minor tasks performed, categorized correctly.
- Detailed analysis of work patterns and trends.
- Distribution and balance of workload across tasks, with accuracy in grouping.
- Key observations and actionable recommendations.
- Identified areas for potential optimization.
- Clear overview of the employee's contributions to different projects and tasks, highlighting any inaccuracies.
""",
            agent=employee_analyst
        ))
    return tasks

def create_general_analysis_task(df: pd.DataFrame) -> list:
    """Create tasks for general timesheet data analysis."""
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []
    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Analyze the following timesheet data to identify key patterns:
{chunk}

Focus on:
1. Total hours spent this month
2. Employee-wise workload distribution
3. Daily trends in hours logged
4. Project-wise time allocation""",
            expected_output="""A detailed analysis report with HTML output containing:
- Total hours calculation
- Employee workload breakdown
- Daily trend analysis
- Project distribution metrics
- Identified patterns and anomalies""",
            agent=data_analyst
        ))
    return tasks

def create_report_task() -> Task:
    """Create a task for generating the final report."""
    return Task(
        description="""Based on the analysis, your role is to create a comprehensive report that includes:

1. A summary of key findings
2. A detailed breakdown of workload distribution
3. Recommendations for workload optimization
4. Notable patterns or concerns

Ensure that the report presents the following information:
- Key findings that highlight the most important insights from the data
- Total hours tracked and the total number of employees
- Workload distribution metrics by employee and by project
- Prioritized recommendations with titles, descriptions, and priority levels
- Identified patterns and concerns, detailing their type, description, and impact

Structure the report clearly with HTML formatting to convey the essential information effectively.""",
        expected_output="""Your task is to generate a comprehensive report in HTML format that includes:
- An executive summary highlighting key findings
- Metrics on workload distribution across employees and projects
- Prioritized recommendations for optimizing workload
- Identified patterns and concerns based on the data

Ensure the output is well-organized and suitable for display in a web browser.""",
        agent=report_writer
    )

# ==============================
# 6. Define Crew Execution Functions
# ==============================

def run_crew(agents: list, tasks: list) -> list:
    """Run the crew with all agents and tasks."""
    try:
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True,
            process=Process.sequential
        )
        result = crew.kickoff()
        return result
    except Exception as e:
        logger.error(f"Error running crew: {e}")
        return []

# ==============================
# 7. Define Analysis Function
# ==============================

def analyze_timesheet_data(user_question: str):
    """
    Main function to analyze timesheet data based on user questions.
    
    Steps:
    1. Authenticate and retrieve access token.
    2. Get SharePoint site ID.
    3. Retrieve timesheet data from SharePoint.
    4. Analyze the user's question to determine analysis type.
    5. Create analysis tasks based on analysis type.
    6. Run the analysis Crew.
    7. Generate and return the report.
    """
    
    try:
        # Step 1: Authentication Task
        auth_task = create_authentication_task()
        auth_crew = Crew(
            agents=[authentication_agent],
            tasks=[auth_task],
            verbose=True,
            process=Process.sequential
        )
        auth_crew.kickoff()
        auth_output = auth_task.output.raw  # Assuming output.raw contains the JSON object
        
        
                # Handle both JSON string and dict formats
        if isinstance(auth_output, str):
            try:
                task_output_raw = json.loads(auth_output)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decoding failed: {e}. Raw output: {auth_output}")
                return "Authentication response is malformed."
        elif isinstance(auth_output, dict):
            task_output_raw = auth_output
        else:
            logger.error(f"Unexpected format for authentication output: {type(auth_output)}")
            return "Unexpected authentication response format."

        access_token = task_output_raw.get('access_token', None)
        if not access_token:
            logger.error("Failed to obtain access token.")
            return "Authentication failed. Please check your credentials."
        
        
        log_file = "SharepointConnection.txt"
        with open(log_file, "a") as f:
            f.write(f"\n\n**Authentication Agent**\n")
            f.write(f"Auth Output: {auth_output}\n")
        task_output_raw = json.loads(auth_task.output.raw)
        access_token = task_output_raw.get('access_token', None)
        with open(log_file, "a") as f:
            f.write(f"Access Token: {task_output_raw.get('access_token')}\n")
        if not access_token:
            logger.error("Failed to obtain access token.")
            return "Authentication failed. Please check your credentials."
        
        # Step 2: Get Site ID Task
        hostname = "maargasystems007.sharepoint.com"
        site_path = "TimesheetSolution"
        site_id_task = create_get_site_id_task(hostname, site_path,access_token)
        site_id_crew = Crew(
            agents=[data_retrieval_agent],
            tasks=[site_id_task],
            verbose=True,
            process=Process.sequential
        )
        site_id_crew.kickoff()
        site_id_output = site_id_task.output.raw
        print("Site ID Output:", site_id_output)
        with open(log_file, "a") as f:
            f.write(f"\n\n**Data Retrieval Agentfor Site ID**\n")
            f.write(f"Site ID Output: {site_id_output}\n")
        site_id_output_data = json.loads(site_id_task.output.raw)
        site_id = site_id_output_data.get('site_id', None)
        with open(log_file, "a") as f:
            f.write(f"Site ID: {site_id}\n")
        if not site_id:
            logger.error("Failed to retrieve site ID.")
            return "Failed to retrieve SharePoint site information."
        
        # Step 3: Retrieve Timesheet Data Task
        select_query = ",".join([
            "Title", "Modified", "Created", "EmployeeName", "Date", "ProjectName", "SOWCode",
            "Module", "Sprint", "TaskOrUserStory", "SubTask", "ActualTimeSpent", "Remarks",
            "Year", "Manager", "SOWCodeSample"
        ])
        filter_query = ""  # Modify if you need specific filtering
        data_task = create_retrieve_timesheet_data_task(
            site_id=site_id,
            list_id=SHAREPOINT_LIST_ID,
            select_query=select_query,
            filter_query=filter_query,
            num_items=NUM_ITEMS
        )
        data_crew = Crew(
            agents=[data_retrieval_agent],
            tasks=[data_task],
            verbose=True,
            process=Process.sequential
        )
        data_crew.kickoff()
        timesheet_df = data_task.output.raw
        with open(log_file, "a") as f:
            f.write(f"\n\n**Data Retrieval Agent for Timesheet Data**\n")
            f.write(f"Timesheet Data: {timesheet_df}\n")
        task_output_raw = json.loads(auth_task.output.raw)
        access_token = task_output_raw.get('access_token', None)
        
        if isinstance(timesheet_df, str):
            # Convert string to DataFrame if necessary
            timesheet_df = pd.read_json(timesheet_df)
        elif isinstance(timesheet_df, dict):
            # Convert dict to DataFrame
            timesheet_df = pd.DataFrame([timesheet_df])
        
        if timesheet_df.empty:
            logger.warning("Timesheet data is empty.")
            return "No timesheet data found."
        
        # Step 4: Analyze User Question
        question_task = create_question_analysis_task(user_question)
        question_crew = Crew(
            agents=[question_analyzer_agent],
            tasks=[question_task],
            verbose=True,
            process=Process.sequential
        )
        question_result = question_crew.kickoff()
        question_output = question_task.output.raw
        analysis_type = question_output.get('Selected analysis type')
        extracted_name = question_output.get('Extracted name')
        time_info = question_output.get('Time-related information')
        
        logger.info(f"Analysis Type: {analysis_type}")
        logger.info(f"Extracted Name: {extracted_name}")
        logger.info(f"Time-related Information: {time_info}")
        
        if not analysis_type:
            logger.warning("Unable to determine analysis type from the question.")
            return "Sorry, I couldn't understand your request. Please try rephrasing the question."
        
        # Step 5: Create Analysis Tasks
        if analysis_type == "Project Analysis" and 'ProjectName' in timesheet_df.columns:
            filtered_df = timesheet_df[timesheet_df['ProjectName'].str.contains(extracted_name, case=False, na=False)].copy()
            if filtered_df.empty:
                logger.warning(f"No data found for project: {extracted_name}")
                return f"No timesheet data found for project '{extracted_name}'."
            analysis_tasks = create_project_analysis_task(filtered_df, extracted_name)
        elif analysis_type == "Employee Analysis" and 'EmployeeName' in timesheet_df.columns:
            filtered_df = timesheet_df[timesheet_df['EmployeeName'].str.contains(extracted_name, case=False, na=False)].copy()
            if filtered_df.empty:
                logger.warning(f"No data found for employee: {extracted_name}")
                return f"No timesheet data found for employee '{extracted_name}'."
            analysis_tasks = create_employee_analysis_task(filtered_df, extracted_name)
        else:
            analysis_tasks = create_general_analysis_task(timesheet_df)
        
        # Step 6: Run Analysis Crew
        analysis_agents = [
            decision_agent, 
            data_analyst, 
            project_analyst, 
            employee_analyst, 
            report_writer
        ]
        analysis_crew = Crew(
            agents=analysis_agents,
            tasks=analysis_tasks + [create_report_task()],
            verbose=True,
            process=Process.sequential
        )
        analysis_result = analysis_crew.kickoff()
        
        # Step 7: Compile and Return Report
        # Assuming that the last task (report_writer) generates the HTML report
        report_task = analysis_crew.tasks[-1]
        report_html = report_task.output.raw  # Assuming output.raw contains HTML content
        
        # Optionally, save the report to an HTML file
        report_filename = f"timesheet_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_filename, 'w') as f:
            f.write(report_html)
        logger.info(f"Report generated and saved as {report_filename}")

        return f"Analysis complete. Report saved as {report_filename}."
    except Exception as e:
        logger.error(f"Error in analyze_timesheet_data: {e}")
        return "An error occurred during analysis. Please try again later."
    
    # ==============================
    # 8. Main Function
    # ==============================

if __name__ == "__main__":
    # Example usage
    user_question = "Give timesheet for project Mahle GPR CR Implementation?"
    result = analyze_timesheet_data(user_question)
    print(result)