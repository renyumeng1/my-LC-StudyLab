# Agent Tools

An agent can call tools when a user request requires information or actions outside the model response. Tools may include calculators, time utilities, web search, weather lookup, file operations, or custom business functions.

## Tool Flow

The model receives the user request and system instructions. If a tool is useful, it emits a tool call with arguments. The application executes the tool and sends the result back to the model. The model then produces a final answer based on the tool result.

## LC-StudyLab Tool Groups

LC-StudyLab has basic tools that do not require external keys and advanced tools that depend on configured services. Weather tools require an AMAP key. Web search tools require a Tavily key.

## Test Prompt

A good test prompt for tools is: "What is the current date, then calculate 18 * 7?" This checks whether the agent can combine tool output with normal reasoning.
