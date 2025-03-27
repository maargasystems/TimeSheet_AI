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

def create_project_analysis_task(df: pd.DataFrame, project_name: str) -> list:
    """Create tasks for analyzing project-specific timesheet data."""
    
    df_str = df.to_string()
    df_chunks = chunk_text(df_str)
    tasks = []

    # for chunk in df_chunks:
    tasks.append(Task(
        description=f"""
            I have a timesheet dataset with {len(df)} entries.
            For each row, I have:
            - ProjectName
            - EmployeeName
            - Date
            - ActualTimeSpent
 
            Please:
            1. Calculate total hours for each employee by month
            2. Break down the totals by project
            3. Verify all entries are included
            4. Format results clearly
 
            Raw data:
            {df.to_string()}
            """,
        agent=project_analyst
    ))
    log_file = "filtered_data_log.txt"    
    with open(log_file, "a") as f:
            f.write(f"\n\n**Project Analysis Agent**\n")
            f.write(f"Project Name: {project_name}\n")
            f.write(f"Tasks: {tasks}\n")
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
                - All calculations must be precise. Ensure that the 'Actualtimespent' column correctly includes floating-point values, as in the following example: 2.0 + 2.5 + 1.5 should equal 6.
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

def analyze_timesheet_data(df: pd.DataFrame, question: str):
    """Main function to analyze timesheet data based on user questions."""
    try:
        # Analyze the question to determine the analysis type and extracted name
        analysis_type, extracted_name, time_info = analyze_question(question)
        log_file = "filtered_data_log.txt"
        with open(log_file, "a") as f:
            f.write(f"\n\n**Analysis Agent**\n")
            f.write(f"Analysis Type: {analysis_type}\n")
            f.write(f"Extracted Name: {extracted_name}\n")
            f.write(f"Time-related Information: {time_info}\n")
        
        # Check if the filtered DataFrame is empty
        if df.empty:
            return "Sorry for the inconvenience, try a different question."       
        # Create analysis tasks based on the analysis type
        tasks = create_analysis_tasks(analysis_type, extracted_name, df, time_info)
        
        # Run the crew with all agents and tasks
        result = run_crew(tasks)
        
        return result
    except Exception as e:
        print(f"Error during analysis: {e}")
        return None

def analyze_question(question: str) -> tuple:
    """Analyze the question to determine the analysis type and extracted name."""
    
    question_analyzer_task = Task(
        description=f"""Analyze the following question to determine if it pertains to Project Analysis, Employee Analysis, or Time Analysis, and extract the relevant details:
        Question: {question}
        
        Available Analysis Types:
        1. Project Analysis - Choose this if the question is related to a specific project.
        2. Employee Analysis - Choose this if the question is related to a specific employee.
        3. Time Analysis - Choose this if the question is related to a specific time period, date, day, month, year or a phrase that related to Calender.
        
        Please provide:
        - The analysis type selected (Project Analysis, Employee Analysis, or Time Analysis).
        - The extracted name (project name or employee name, if applicable).
        - Any specific time-related information (Year, Month, Day, or Date) if mentioned in the question. Return "Year" if the question pertains to a Year, "Month" for Months, "Day" for Days, or "Date" if it is about a specific Date.""",
        expected_output="""A decision object containing the following information in JSON format:
        - Selected analysis type (Project Analysis, Employee Analysis, or Time Analysis)
        - Extracted name (project name or employee name, if applicable)
        - Time-related information (Year, Month, Day, or Date, if specified)""",
        agent=question_analyzer_agent
    )
    
    questionAnalyserCrew = Crew(
        agents=[question_analyzer_agent],
        tasks=[question_analyzer_task],
        verbose=True,
        process=Process.sequential
    )
    
    questionAnalyserCrew.kickoff()
    task_output = question_analyzer_task.output

    # Handle empty or invalid output
    if not task_output or not hasattr(task_output, 'raw'):
        print("Error: Task output is empty or not structured correctly.")
        return None, None, None

    try:
        task_output_raw = json.loads(task_output.raw)
    except json.JSONDecodeError as e:
        print(f"JSON decoding failed: {e}. Raw output: {task_output.raw}")
        return None, None, None

    # Extract results
    analysis_type = task_output_raw.get('Selected analysis type', None)
    extracted_name = task_output_raw.get('Extracted name', None)
    time_info = task_output_raw.get('Time-related information', None)  # This is to capture any time-related info

    print("Analysis Type:", analysis_type)
    print("Extracted Name:", extracted_name)
    print("Time-related Information:", time_info)  # For debugging

    return analysis_type, extracted_name, time_info  # Return time info as well

def create_analysis_tasks(analysis_type: str, extracted_name: str, filtered_df: pd.DataFrame,time_info:any) -> list:
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