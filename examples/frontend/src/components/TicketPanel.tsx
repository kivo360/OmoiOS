import React, { useState } from "react";

type Ticket = {
  id: string;
  title: string;
  description: string;
  workspaceDir: string;
  aiSummary?: string | null;
};

type RunResult = {
  ticket_id: string;
  status: string;
  summary: string;
};

export function TicketPanel({ ticket }: { ticket: Ticket }) {
  const [aiSummary, setAiSummary] = useState(ticket.aiSummary ?? "");
  const [status, setStatus] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function runAi() {
    setRunning(true);
    try {
      const res = await fetch("/api/tickets/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticket_id: ticket.id,
          title: ticket.title,
          description: ticket.description,
          workspace_dir: ticket.workspaceDir,
        }),
      });

      if (!res.ok) {
        throw new Error(`Request failed with status ${res.status}`);
      }

      const data: RunResult = await res.json();
      setAiSummary(data.summary);
      setStatus(data.status);
    } catch (err) {
      console.error(err);
      setStatus("error");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 border rounded-lg p-4 bg-white">
      <h2 className="font-semibold text-lg">{ticket.title}</h2>
      <p className="text-sm whitespace-pre-wrap text-gray-700">{ticket.description}</p>
      <button
        onClick={runAi}
        disabled={running}
        className="px-3 py-1 rounded bg-black text-white disabled:opacity-60 hover:bg-gray-800 transition-colors"
      >
        {running ? "Running AI…" : "Run AI on this ticket"}
      </button>
      {status && (
        <div className="text-xs text-gray-500">
          Agent status: <strong>{status}</strong>
        </div>
      )}
      {aiSummary && (
        <div className="mt-3">
          <h3 className="font-semibold text-sm mb-1">Last AI Summary</h3>
          <pre className="text-xs bg-gray-100 rounded p-2 whitespace-pre-wrap overflow-auto">
            {aiSummary}
          </pre>
        </div>
      )}
    </div>
  );
}

