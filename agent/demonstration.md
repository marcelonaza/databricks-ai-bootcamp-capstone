# Weather Agent validation scenarios

Use these scenarios after registering the deployed Weather MCP server in Databricks AI Playground. For each successful scenario, confirm both the visible tool call and the final grounded answer.

## 1. Current conditions

**Prompt**

```text
What is the current weather in Lisbon, Portugal?
```

**Expected behavior**

- Calls `get_current_weather`.
- Uses the resolved location returned by the tool.
- Reports current values with the returned units.
- Identifies Open-Meteo as the data source.

## 2. Multi-day forecast

**Prompt**

```text
Will it rain in Chicago over the next three days?
```

**Expected behavior**

- Calls `get_forecast` with `days=3`.
- Bases the rain summary only on the returned forecast.
- States that forecasts can change.

## 3. Practical recommendation

**Prompt**

```text
Should I bring an umbrella or jacket to Austin tomorrow?
```

**Expected behavior**

- Converts “tomorrow” to an ISO date.
- Calls `get_weather_recommendation`.
- Explains the recommendation using returned forecast values and triggered rules.

## 4. Error handling

**Prompt**

```text
What is the weather in X?
```

**Expected behavior**

- Surfaces the clean location error.
- Requests a clearer city, country, or region.
- Does not invent weather data.

## Evidence checklist

- MCP App deployment is running.
- All three tools are visible in AI Playground.
- Each successful prompt shows the expected tool call.
- Final answers remain grounded in tool output.
- The invalid-location prompt produces no fabricated values.
