from agent.agent_setup import run_agent

results = []
while (enough := input("Enter your query: ")) != "cancel":
    message = enough + "\nIf there is a query linked with article then send the user a pdf_url. It's so important"
    result = run_agent(message)
    results.append(result)
print(results)
