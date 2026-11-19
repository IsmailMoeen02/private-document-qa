# n8n version

`workflow.json`: chat message (test webhook, or a Slack trigger that is disabled until an account is connected) -> Code step (sender and question) -> HTTP Request to Private Q&A as that sender -> Switch (answered / no answer) -> reply text with source -> chat post -> reply.

1. Run Private Q&A with `INBOUND_KEY=demo-inbound-key` on port 8796 (or edit the URL and key in the "Ask the documents" node), and seed it.
2. In n8n, Import from file -> `workflow.json`, then Publish. `python n8n/run_in_n8n.py` does the import and four test questions through the n8n REST API.
3. `python n8n/fake_slack.py 8799` starts a local stand-in for a Slack incoming webhook.
4. Ask: POST `{"user": "ayesha", "question": "..."}` to `/webhook/ask-documents`.

`python n8n/build_workflow.py > n8n/workflow.json` regenerates the file.
