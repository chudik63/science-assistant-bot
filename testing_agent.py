from agent import Agent

biba = Agent(token="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")

while True:
    message = input("Query: ")
    if message == "stop":
        break
    result = biba.run_agent(message)
    print(result)