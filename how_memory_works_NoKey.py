import os
from dotenv import load_dotenv
from crewai import Crew, Agent, Task, Process
from crewai.memory.short_term.short_term_memory import ShortTermMemory
from crewai.memory.storage.rag_storage import RAGStorage
load_dotenv()
MY_OPENAI_API_KEY= "KEY"
os.environ["OPENAI_API_KEY"] = MY_OPENAI_API_KEY
# Define the father agent
father_agent = Agent(
    role='Father',
    goal='You are the father of a kid. The kid may ask you any question. '
         'Your goal is to provide a satisfactory answer to the kid.',
    verbose=True,
    memory=True,
    backstory="You are a 40-year-old male living in San Jose with your wife and 10-year-old kid.",
    tools=[],
    allow_delegation=True
)

# Define the task
father_task = Task(
    description="Your task is to answer the {question} of your kid in a satisfactory and understandable way.",
    expected_output='Answer to your kid question',
    tools=[],
    agent=father_agent
)

# Initialize the crew with memory
parent_crew = Crew(
    agents=[father_agent],
    tasks=[father_task],
    process=Process.sequential,
    memory=True,
    short_term_memory=ShortTermMemory(
        storage=RAGStorage(
            type="short_term",
            allow_reset=True,
            embedder_config={
                "provider": "openai",
                "config": {
                    "model": "text-embedding-ada-002",
                    "api_key": MY_OPENAI_API_KEY
                }
            },
            path=r"C:\Users\zadeh\Desktop\Mehdi_Documents\projects\Crew_ai_sample\crewai_memory\db\short_term"
        )
    ),
    verbose=True,
    embedder={
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small"
        }
    }
)

# Interactive loop
while True:
    question = input("Kid: \n")
    answer = parent_crew.kickoff({"question": question})
    print("***********************")
    print(answer)
