---
name: upsell
description: analyses an organisation, starts from analysing automation blockers and drills down into logs to find out reasons for the blockers and offers solutions.
---

DO NOT:
 - make up numbers, use only data that you retrieve.
 - try to implement any of the changes

1. Ask user for an organisation ID, base URL and API token.
2. use the information to query endpoint "rossum_queue_automation" with reasonable timeframe - past 2 months is enough. analyse all PRODUCTION queues in the organisation. Focus only on production ones - you should be able to tell by the workspace/queue name. If there's no word production found, exclude any queues/workspaces that contain any of TEST DEV UAT words.
3. Analyse kibana logs using skill analyze-kibana-logs. Use the same input parameters as before. Analyse the blockers from this endpoint and use this knowledge later.
4. connect the dots between the kibana logs, failures and the automation blockers and suggest possible improvements - either use your own knowledge or skill analyze.
5. do not spend time to validate your assumptions yet, provide analysis report and as if more thorough analysis should be performed

Output:
Provide a table of each suggestion with possible impact and effort.
Follow this table with more detailed description of the suggestion but without going into too much detail or solutioning.
Always list affected hooks or queues where the improvements are to be done.