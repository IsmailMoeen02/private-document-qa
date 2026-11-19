"""Writes workflow.json: staff questions from chat, answered from their own documents.  python n8n/build_workflow.py > n8n/workflow.json"""
import json, uuid
def node(name, type_, v, pos, params=None, **kw):
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "pq" + name)), "name": name, "type": type_, "typeVersion": v, "position": pos, "parameters": params or {}, **kw}

PREPARE = """// The test inbox sends {user, question}. A chat trigger sends the sender and the message text. Both become the same request.
const b = $input.first().json.body && typeof $input.first().json.body === 'object' ? $input.first().json.body : $input.first().json;
const user = String(b.user || b.username || b.sender || '').trim().toLowerCase();
const question = String(b.question || b.text || b.message || '').trim().slice(0, 500);
if (!user) throw new Error('No sender on this message');
if (question.length < 2) throw new Error('No question on this message');
return [{ json: { user, question } }];"""
def cond(val): return {"options": {"caseSensitive": True, "typeValidation": "loose", "version": 2}, "combinator": "and", "conditions": [{"leftValue": "={{ $json.outcome }}", "rightValue": val, "operator": {"type": "string", "operation": "equals"}}]}
ANSWERED = "={{ $json.answer + '\\n\\nSource: ' + $json.citations[0].title + ', ' + $json.citations[0].heading + ($json.citations[0].page ? ', page ' + $json.citations[0].page : '') }}"
NOANSWER = "={{ 'I could not find this in the documents you have access to. It has been logged so the document owner can see what is missing.' }}"
nodes = [
 node("Question from chat (test inbox)", "n8n-nodes-base.webhook", 2, [0, 140], {"httpMethod": "POST", "path": "ask-documents", "responseMode": "responseNode", "options": {}}, webhookId="a1b2c3d4-2222-4333-8444-555566667788"),
 node("New chat message (production)", "n8n-nodes-base.slackTrigger", 1, [0, 360], {"trigger": ["message"], "channelId": {"__rl": True, "mode": "list", "value": ""}, "options": {}}, disabled=True,
      notes="Switch this on, pick the Slack or Teams account and channel. The message text becomes the question and the sender's name picks whose documents are searched."),
 node("Prepare question", "n8n-nodes-base.code", 2, [260, 240], {"jsCode": PREPARE}),
 node("Ask the documents", "n8n-nodes-base.httpRequest", 4.2, [520, 240], {"method": "POST", "url": "http://127.0.0.1:8796/api/inbound/ask", "sendHeaders": True,
      "headerParameters": {"parameters": [{"name": "X-Inbound-Key", "value": "demo-inbound-key"}]}, "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json) }}", "options": {"timeout": 60000}},
      notes="Asks as that person, so the answer can only come from documents they may read."),
 node("Found an answer?", "n8n-nodes-base.switch", 3.2, [780, 220], {"rules": {"values": [{"conditions": cond("answered"), "renameOutput": True, "outputKey": "Answered"}]},
      "options": {"fallbackOutput": "extra", "renameFallbackOutput": "No answer"}}),
 node("Write reply with source", "n8n-nodes-base.set", 3.4, [1040, 120], {"assignments": {"assignments": [{"id": "a1", "name": "text", "type": "string", "value": ANSWERED}]}, "options": {}}),
 node("Write no-answer reply", "n8n-nodes-base.set", 3.4, [1040, 340], {"assignments": {"assignments": [{"id": "a2", "name": "text", "type": "string", "value": NOANSWER}]}, "options": {}}),
 node("Post to chat", "n8n-nodes-base.httpRequest", 4.2, [1300, 240], {"method": "POST", "url": "http://127.0.0.1:8799/", "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify({ text: $json.text }) }}", "options": {}},
      notes="Points at a local stand-in for a Slack incoming webhook. Replace the URL with a real one."),
 node("Reply with result", "n8n-nodes-base.respondToWebhook", 1.1, [1560, 240], {"respondWith": "json", "responseBody": "={{ JSON.stringify($('Ask the documents').first().json) }}", "options": {}}, executeOnce=True),
]
def c(*t): return {"main": [[{"node": x, "type": "main", "index": 0} for x in t]]}
connections = {"Question from chat (test inbox)": c("Prepare question"), "New chat message (production)": c("Prepare question"), "Prepare question": c("Ask the documents"), "Ask the documents": c("Found an answer?"),
 "Found an answer?": {"main": [[{"node": "Write reply with source", "type": "main", "index": 0}], [{"node": "Write no-answer reply", "type": "main", "index": 0}]]},
 "Write reply with source": c("Post to chat"), "Write no-answer reply": c("Post to chat"), "Post to chat": c("Reply with result")}
print(json.dumps({"name": "Staff questions from chat: Private Q&A", "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}}, indent=1))
