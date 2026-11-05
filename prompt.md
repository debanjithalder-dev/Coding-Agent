We want to make a coding agent in python which can solve simple bugs. We will use the groq LLM for this purpose and look in the past files, to know the model which one to use.

The LLM will have some tools which will help in solving the bug.
1) One tool will be there which will be able to search files, which lists the path of files, related to the bug as per the LLM.
2) One tool will be there to search inside the file, that will give the line number related to the bug.
3) One replacing tool will be present which allows replacing a line with another line.

For testing purpose, I will test it myself. Prepare a simple .cpp file and write the boiler plate code in it. Dont introduce any bug by yourself. I will introduce a bug and test it myself.

I want to give the bug in simple english. The LLM and the tools should be able to solve it. Make the system w/o langgraph and keep it simple. Also there will be a max retry of 3 attempts. If the LLM cant solve the bug within this limit, it should print a message saying that it cannot solve the bug.

Also there should be clear print statements saying which tool was called at each step. We want to understand the flow completely. As soon as I change the cpp file and run the agent it should as me my bug. After I give my bug, it should begin solving it.
Dont write any test cases for now. If anything is unclear ask mee.