import pandas as pd
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
import os
from datetime import datetime
import json

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Helper function to format data as HTML tables
def format_as_html_table(dataframe: pd.DataFrame, title: str) -> str:
    """Convert a pandas DataFrame to an HTML table."""
    html = f"<h3>{title}</h3>"
    html += dataframe.to_html(index=False, border=0, classes='dataframe table table-bordered', justify='center')
    return html

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
    in a structured, actionable HTML format. You focus on creating clear tables that highlight key findings
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
    without any additional comments or explanations. 
    For example, return: 
    filtered_data = df[df['ProjectName'].str.contains('McKinsey_LN Support_2', case=False, na=False)]""",
    verbose=True,
    allow_delegation=False
)

question_analyzer_agent = Agent(
    role='Question Analyzer',
    goal='Analyze the user question to determine if it pertains to a project or an employee and extract the relevant name.',
    backstory="""You are an expert in natural language processing. 
    Your task is to analyze the user's question and determine whether it pertains to a project or an employee. 
    You will also extract the relevant project name or employee name from the question.""",
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
    """Create filter tasks based on the user question and DataFrame."""
    df_str = df.head(5000).to_string()  # Only send top 5000 records to the agent
    df_chunks = chunk_text(df_str)
    tasks = []
    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Write and execute the filter condition to filter the data from the DataFrame based on the user question:
            Question: {question}
            
            DataFrame columns: {df.columns.tolist()}
            
            DataFrame chunk:
            {chunk}
            
            The filter condition should be written in Python and returned as a query string.
            
            Ensure that the filter query is valid and executable. For example:
            filtered_data = df[(df['ProjectName'] == 'KanTime AI Project') & (pd.to_datetime(df['Date']) >= pd.to_datetime('today') - pd.DateOffset(months=2))]""",
            expected_output="""A Python filter query string that can be applied to the DataFrame to retrieve the relevant data.""",
            agent=filter_agent
        ))
    return tasks

def create_employee_analysis_task(df: pd.DataFrame, employee_id: str) -> list:
    """Create tasks for analyzing employee-specific timesheet data."""
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
            expected_output="""A detailed employee analysis report with HTML output containing:
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
    """Create tasks for analyzing project-specific timesheet data."""
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []
    for chunk in df_chunks:
        tasks.append(Task(
            description=f"""Analyze the timesheet data for project '{project_name}':
            {chunk}
            
            Focus on:
            1. Total hours spent on this project
            2. Employee contribution distribution
            3. Daily/Weekly effort patterns
            4. Resource utilization trends
            5. Peak activity periods""",
            expected_output="""A detailed project analysis report with HTML output containing:
            - Project hours summary
            - Resource allocation breakdown
            - Temporal effort patterns
            - Resource utilization metrics
            - Key observations and recommendations
            - The Task the employee is worked on most
            """,
            agent=project_analyst
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

def log_filtered_data(question: str, filter_query: str, filtered_data: pd.DataFrame):
    """Log the filtered data along with the question, filter query, and timestamp to a text file."""
    log_file = "filtered_data_log.txt"
    with open(log_file, "a") as f:
        f.write(f"Question: {question}\n")
        f.write(f"Filter Query: {filter_query}\n")
        f.write(f"Time: {datetime.now()}\n")
        f.write("Filtered Data:\n")
        f.write(filtered_data.to_string())
        f.write("\n\n")

def filter_dataframe(df, filter_code):
    """Execute the filter code dynamically and return the filtered DataFrame."""
    print("Initial DataFrame (ProjectName column):\n", df['ProjectName'])
#     filter_code="""filtered_data = df[
#     (df['ProjectName'] == 'KanTime AI Project') & 
#     (df['Date'] >= (pd.to_datetime('today') - pd.DateOffset(months=2)).strftime('%d/%m/%Y'))
# ]"""
    print("Filter code:\n", filter_code)
    # Prepare a local context for the exec call
    local_context = {'df': df, 'pd': pd}  # Include pandas in the local context
    filter_code_str = str(filter_code)

    # Execute the filter code dynamically
    exec(filter_code_str, {}, local_context)  
    print("Executed filter code.")

    # Retrieve filtered_data from local_context
    filtered_data = local_context.get('filtered_data', None)

    # Debugging: Print the filter result
    if filtered_data is not None:
        print("Filter result:\n", filtered_data)
    else:
        print("No filtered data returned.")

    # Limit the filtered DataFrame to the top 5000 rows
    filtered_data = filtered_data.head(5000) if filtered_data is not None else pd.DataFrame()

    return filtered_data, filter_code_str

def analyze_timesheet_data(df: pd.DataFrame, question: str):
    """Main function to analyze timesheet data based on user questions."""
    try:
        # Clean and sort DataFrame
        df = clean_and_sort_dataframe(df)
        
        # Analyze the question to determine the analysis type and extracted name
        analysis_type, extracted_name = analyze_question(question)
        
        # Filter the DataFrame based on the question
        filtered_df, filter_query_python = filter_data(df, question)
        
        # Log the filtered data
        log_filtered_data(question, filter_query_python, filtered_df)
        
        # Create analysis tasks based on the analysis type
        tasks = create_analysis_tasks(analysis_type, extracted_name, filtered_df)
        
        # Add report task as the final task
        tasks.append(create_report_task())
        
        # Run the crew with all agents and tasks
        result = run_crew(tasks)
        
        return result
    except Exception as e:
        print(f"Error during analysis: {e}")
        return None

def clean_and_sort_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and sort the DataFrame."""
    df.columns = [col.replace('[', '').replace(']', '') for col in df.columns]
    df = df.sort_values(by='Modified', ascending=False)
    return df

def analyze_question(question: str) -> tuple:
    """Analyze the question to determine the analysis type and extracted name."""
    question_analyzer_task = Task(
        description=f"""Analyze the following question to determine if it pertains to a Project Analysis or an Employee Analysis and extract the relevant name:
        Question: {question}
        
        Available Analysis Types:
        1. Project Analysis
        2. Employee Analysis
        
        Provide the analysis type and the extracted name.""",
        expected_output="""A decision object containing given in string format:
        - Selected analysis type (Project Analysis or Employee Analysis)
        - Extracted name (project name or employee name)""",
        agent=question_analyzer_agent
    )
    questionAnalyserCrew = Crew(
        agents=[question_analyzer_agent],
        tasks=[question_analyzer_task],
        verbose=True,
        process=Process.sequential
    )
    result = questionAnalyserCrew.kickoff()
    task_output = question_analyzer_task.output
    task_output_raw = json.loads(task_output.raw)
    analysis_type = task_output_raw.get('Selected analysis type', None)
    extracted_name = task_output_raw.get('Extracted name', None)
    return analysis_type, extracted_name

def filter_data(df: pd.DataFrame, question: str) -> pd.DataFrame:
    """Filter the DataFrame based on the question."""
    filter_tasks = create_filter_task(df, question)
    fcrew = Crew(
        agents=[filter_agent],
        tasks=filter_tasks,
        verbose=True,
        process=Process.sequential
    )
    filter_result = fcrew.kickoff()
    filter_query = filter_result
    print("Filter query:", filter_query)
    filtered_df, _ = filter_dataframe(df, filter_query)
    return filtered_df, filter_query

def create_analysis_tasks(analysis_type: str, extracted_name: str, filtered_df: pd.DataFrame) -> list:
    """Create analysis tasks based on the analysis type."""
    tasks = []
    if analysis_type == "Project Analysis" and 'ProjectName' in filtered_df.columns:
        project_df = filtered_df[filtered_df['ProjectName'].str.contains(extracted_name, case=False, na=False)].copy()
        if not project_df.empty:
            tasks.extend(create_project_analysis_task(project_df, extracted_name))
        else:
            print(f"No project data found for: {extracted_name}")
    elif analysis_type == "Employee Analysis" and 'EmployeeName' in filtered_df.columns:
        employee_df = filtered_df[filtered_df['EmployeeName'].str.contains(extracted_name, case=False, na=False)].copy()
        if not employee_df.empty:
            tasks.extend(create_employee_analysis_task(employee_df, extracted_name))
        else:
            print(f"No employee data found for: {extracted_name}")
    else:
        tasks.extend(create_general_analysis_task(filtered_df))
    return tasks

def run_crew(tasks: list) -> dict:
    """Run the crew with all agents and tasks."""
    crew = Crew(
        agents=[decision_agent, data_analyst, project_analyst, employee_analyst, report_writer],
        tasks=tasks,
        verbose=True,
        process=Process.sequential
    )
    result = crew.kickoff()
    return result