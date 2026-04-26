# 10 · Client Patterns

The point of a multi-client architecture: **one session, many surfaces**. A developer kicks off a fix from their IDE; their teammate watches from Slack; CI attaches to verify the PR; the PM drops a comment from a web view. Three patterns cover 90 % of this.

| Client | When | How |
|---|---|---|
| **Slack bot** | Non-engineers, chat-native UX. | Slash command → `sessions.create` → webhook → post to thread. |
| **CI / cron** | Automation, gate conditions. | `sessions.create` + sync wait on events iterator, exit code = status. |
| **Web + editor** | Engineers who want the full streamed IDE view. | React + `sessions.connect` (WebSocket) + hosted IDE iframe. |

The unifying pattern: every client talks to the same session actor. `metadata.origin` on the create request is surfaced in every downstream event, so your Slack bot can format PR links differently from your CI integration while they're watching the same live state.

---

## 1 · Slack slash command

The bot runs on the tenant's infra with their platform key. Creates the session, stashes the thread timestamp, lets the webhook dispatcher do the rest.

```ts
app.command("/agent", async ({ command, ack, respond }) => {
  await ack();

  const session = await agent.sessions.create({
    workspace_id: mapChannelToWorkspace(command.channel_id),
    prompt: command.text,
    metadata: {
      origin: "slack",
      slack_channel: command.channel_id,
      slack_user:    command.user_id,
    },
  });

  const { ts } = await respond({
    text: `🧵 started \`${session.id}\` — streaming here`,
    response_type: "in_channel",
  });

  await kv.set(`session:${session.id}`, { channel: command.channel_id, ts });
});

// Webhook handler
app.post("/hooks/agent", async (req, res) => {
  if (!verifyHmac(req)) return res.status(401).end();
  const evt = req.body;

  if (evt.type === "session.succeeded") {
    const ctx = await kv.get(`session:${evt.data.session_id}`);
    await slack.chat.postMessage({
      channel: ctx.channel,
      thread_ts: ctx.ts,
      text: `✅ done — ${evt.data.artifacts.map(a => a.external_url).join(" ")}`,
    });
  }
  res.status(200).end();
});
```

---

## 2 · GitHub Action

Synchronous pattern: the workflow blocks until the session ends. Useful for gating downstream steps on agent success.

```yaml
name: agent-fix-failing-tests
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  fix:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: dispatch agent
        env:
          PLATFORM_KEY: ${{ secrets.AGENT_PLATFORM_KEY }}
          AGENT_ORG: ${{ vars.AGENT_ORG }}
          AGENT_WORKSPACE: ${{ vars.AGENT_WORKSPACE }}
        run: |
          pip install agent-sdk
          python - <<'EOF'
          import asyncio, os, sys
          from agent_sdk import AgentClient

          async def main():
              async with AgentClient(
                  org_id=os.environ["AGENT_ORG"],
                  api_key=os.environ["PLATFORM_KEY"],
              ) as client:
                  s = await client.sessions.create(
                      workspace_id=os.environ["AGENT_WORKSPACE"],
                      prompt=f"Fix failing test in run {os.environ['GITHUB_RUN_ID']}",
                  )
                  async for evt in client.sessions.events(s.id):
                      if evt.type == "session_ended":
                          print(f"::notice::session {evt.data['status']}")
                          sys.exit(0 if evt.data["status"] == "succeeded" else 1)

          asyncio.run(main())
          EOF
```

---

## 3 · Web client with streamed editor

Platform provides a hosted editor URL for every running session. The customer's web app embeds it in an iframe and decorates it with their own UI. This is how Ramp gets a full VS Code view with zero per-tenant maintenance.

```tsx
export function SessionView({ sessionId, userToken }: Props) {
  const [events, setEvents] = useState<Event[]>([]);
  const [status, setStatus] = useState("pending");
  const channelRef = useRef<SessionChannel | null>(null);

  useEffect(() => {
    const channel = client.sessions.connect(sessionId, userToken);
    channelRef.current = channel;
    channel.on("*", (evt) => {
      setEvents(prev => [...prev, evt]);
      if (evt.type === "status_change") setStatus(evt.data.to);
    });
    return () => channel.close();
  }, [sessionId]);

  const send = (text: string) =>
    channelRef.current?.send({ type: "message.send", data: { text } });

  return (
    <div className="grid grid-cols-[380px_1fr] h-screen">
      <aside className="border-r overflow-auto p-4">
        <StatusPill status={status} />
        <EventLog events={events} />
        <ComposeBox onSend={send} />
      </aside>
      <iframe
        src={`https://ide.example.com/s/${sessionId}?token=${userToken}`}
        className="border-0"
        allow="clipboard-read; clipboard-write"
      />
    </div>
  );
}
```
