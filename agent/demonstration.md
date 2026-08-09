# Agent demonstration checklist

Capture the visible tool call and final answer for each prompt after registering the deployed MCP server in Agent Bricks.

1. `What is the current weather in Lisbon, Portugal?`
   - Expected tool: `get_current_weather`
2. `Will it rain in Chicago over the next three days?`
   - Expected tool: `get_forecast` with `days=3`
3. `Should I bring an umbrella or jacket to Austin tomorrow?`
   - Expected tool: `get_weather_recommendation` with tomorrow as `YYYY-MM-DD`
4. Error-handling evidence: `What is the weather in X?`
   - Expected behavior: clean error and request for a clearer location; no invented data.

Store screenshots in `docs/screenshots/` and replace this checklist with the actual observed outputs before final submission.
