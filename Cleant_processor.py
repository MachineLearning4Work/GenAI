import json
import re
import yaml
from crewai import Agent, Task, CrewBase, Tool
from pydantic import BaseModel
from typing import Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Pydantic model for JSON validation
class ContractData(BaseModel):
    contract_metadata: Dict[str, Any]
    financials: Dict[str, Any]
    exclusion: Dict[str, Any]
    payment_terms: Dict[str, Any]
    billing_instructions: Dict[str, Any]
    exceptions_or_notes: str
    signature: Dict[str, Any]
    services: Dict[str, Any]
    roles: Dict[str, Any]
    service_level_agreements: Dict[str, Any]

# Standardization function (used as a tool)
def standardize_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardizes fields like location, vendor, etc., in the JSON data.
    """
    try:
        # Standardize location (e.g., convert to uppercase, remove extra spaces)
        if "location" in data["contract_metadata"]:
            data["contract_metadata"]["location"] = re.sub(
                r'\s+', ' ', data["contract_metadata"]["location"].strip()
            ).upper()

        # Standardize vendor (e.g., title case, remove special characters)
        if "vendor" in data["contract_metadata"]:
            data["contract_metadata"]["vendor"] = re.sub(
                r'[^a-zA-Z0-9\s]', '', data["contract_metadata"]["vendor"].strip()
            ).title()

        # Standardize financial amounts (e.g., ensure two decimal places)
        if "amount" in data["financials"]:
            try:
                data["financials"]["amount"] = f"{float(data['financials']['amount']):.2f}"
            except (ValueError, TypeError):
                logger.warning("Invalid financial amount format")

        # Standardize payment terms (e.g., convert to uppercase)
        if "terms" in data["payment_terms"]:
            data["payment_terms"]["terms"] = data["payment_terms"]["terms"].upper()

        return data
    except Exception as e:
        logger.error(f"Error in standardization: {str(e)}")
        return data

# Validation function for input/output (used as a tool)
def validate_json(json_data: Dict[str, Any], is_output: bool = False) -> bool:
    """
    Validates JSON structure and, for output, checks standardized fields.
    """
    try:
        ContractData(**json_data)
        if is_output:
            # Check if location is uppercase
            if "location" in json_data["contract_metadata"]:
                assert json_data["contract_metadata"]["location"] == json_data["contract_metadata"]["location"].upper()
            # Check if vendor is title case
            if "vendor" in json_data["contract_metadata"]:
                assert json_data["contract_metadata"]["vendor"] == json_data["contract_metadata"]["vendor"].title()
            logger.info("Output JSON validation successful")
        else:
            logger.info("Input JSON validation successful")
        return True
    except Exception as e:
        logger.error(f"{'Output' if is_output else 'Input'} JSON validation failed: {str(e)}")
        return False

# Define Tools
validation_tool = Tool(
    name="JSON Validator",
    func=validate_json,
    description="Validates JSON structure and standardized fields."
)

standardization_tool = Tool(
    name="Field Standardizer",
    func=standardize_fields,
    description="Standardizes fields like location, vendor, and financials in JSON data."
)

@CrewBase
class ContractProcessingCrew:
    def __init__(self):
        self.agents_config = None
        self.tasks_config = None
        self.input_json = None
        self.sample_json = {
            "contract_metadata": {
                "location": " new york  ",
                "vendor": "acme@corp!"
            },
            "financials": {
                "amount": "1000.5"
            },
            "exclusion": {},
            "payment_terms": {
                "terms": "net 30"
            },
            "billing_instructions": {},
            "exceptions_or_notes": "None",
            "signature": {},
            "services": {},
            "roles": {},
            "service_level_agreements": {}
        }

    @before_kickoff
    def setup(self, inputs: Dict[str, Any]) -> None:
        """Load YAML configurations and store input JSON before starting the crew."""
        try:
            with open("agent.yaml", "r") as f:
                self.agents_config = yaml.safe_load(f)
            with open("tasks.yaml", "r") as f:
                self.tasks_config = yaml.safe_load(f)
            logger.info("Successfully loaded agent.yaml and tasks.yaml")
            self.input_json = inputs.get("json_data", self.sample_json)
        except FileNotFoundError as e:
            logger.error(f"Configuration file missing: {str(e)}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML format: {str(e)}")
            raise

    @agent
    def data_validator(self) -> Agent:
        """Define Data Validator agent using YAML configuration."""
        if "data_validator" not in self.agents_config:
            raise ValueError("data_validator not found in agent.yaml")
        return Agent(
            config=self.agents_config["data_validator"],
            tools=[validation_tool],
            verbose=True
        )

    @agent
    def data_standardizer(self) -> Agent:
        """Define Data Standardizer agent using YAML configuration."""
        if "data_standardizer" not in self.agents_config:
            raise ValueError("data_standardizer not found in agent.yaml")
        return Agent(
            config=self.agents_config["data_standardizer"],
            tools=[standardization_tool],
            verbose=True
        )

    @task
    def validate_input(self) -> Task:
        """Define input validation task using YAML configuration."""
        if "validate_input" not in self.tasks_config:
            raise ValueError("validate_input task not found in tasks.yaml")
        return Task(
            config=self.tasks_config["validate_input"],
            agent=self.data_validator(),
            inputs={"json_data": self.input_json}
        )

    @task
    def standardize_data(self) -> Task:
        """Define data standardization task using YAML configuration."""
        if "standardize_data" not in self.tasks_config:
            raise ValueError("standardize_data task not found in tasks.yaml")
        return Task(
            config=self.tasks_config["standardize_data"],
            agent=self.data_standardizer(),
            inputs={"json_data": self.input_json}
        )

    @task
    def validate_output(self) -> Task:
        """Define output validation task using YAML configuration."""
        if "validate_output" not in self.tasks_config:
            raise ValueError("validate_output task not found in tasks.yaml")
        return Task(
            config=self.tasks_config["validate_output"],
            agent=self.data_validator(),
            inputs={"json_data": self.standardize_data().execute()}
        )

    @crew
    def crew(self) -> None:
        """Define the crew with agents and tasks."""
        self._crew = Crew(
            agents=[self.data_validator(), self.data_standardizer()],
            tasks=[self.validate_input(), self.standardize_data(), self.validate_output()],
            verbose=True
        )

    @after_kickoff
    def finalize(self, result: Any) -> Any:
        """Log and return the final result after crew execution."""
        logger.info(f"Processed JSON: {json.dumps(result, indent=2)}")
        return result

# Example usage
if __name__ == "__main__":
    crew = ContractProcessingCrew()
    result = crew.run(inputs={"json_data": crew.sample_json})