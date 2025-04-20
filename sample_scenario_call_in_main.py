@listen("data_scenario_analysis")
def scenario_analysis_crew(self):
    # 1. Extract user intent from the identified use case
    user_intent = str(self.state['identify_use_case_task'])

    # 2. Build structured_request(s) from pydantic changes
    json_data = [
        {**change.dict(), "user_input": user_intent}
        for change in self.state['identify_use_case_task'].pydantic_changes
    ]
    
    structured_request = json_data[0]  # Or loop over all if needed

    # 3. Prepare inputs for the Crew
    self.inputs.update({
        "user_intent": user_intent,
        "structured_request": structured_request
    })

    # 4. Run the Crew
    self.answer = ScenarioAnalysisCrew().crew.kickoff(inputs=self.inputs)

    # 5. Update state with results
    self.state['build_execute_scenario'] = self.answer
    self.state['answer'] = self.answer

    return self.answer
