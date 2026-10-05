from agent_router import answer_message


print("Starting...")

while True:
    print("************************")
    question = input("Question: ")
    
    print("type 'exit' to quit")
    if question == "exit":
        break

    response = answer_message(question)
    print(f"Intent: {response['intent']}")
    print(response["answer"])

    if response.get("tool_result"):
        print("Tool result:")
        print(response["tool_result"])

    if response.get("sources"):
        print("Source nodes:")
        for source in response["sources"]:
            print("---")
            print(source["text"])
            print({"file_name": source["file_name"], "file_path": source["file_path"]})
