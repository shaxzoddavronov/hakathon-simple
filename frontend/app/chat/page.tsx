"use client";

import { useEffect, useRef, useState } from "react";

import { GlassPanel } from "@/components/GlassPanel";
import { MessageBubble } from "@/components/MessageBubble";
import { DatabaseIcon, MicIcon, SendIcon, SparkIcon, TrendIcon } from "@/components/icons";
import { api, getToken, streamChat } from "@/lib/api";
import type { ChatMessage, UISpec } from "@/lib/types";

type WorkspaceOut = { id: string; name: string; dialect: string; status: string };

const SUGGESTIONS = [
  "Show monthly trends",
  "Breakdown by region",
  "Top customers",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [authMissing, setAuthMissing] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceOut[]>([]);
  const [activeWs, setActiveWs] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!getToken()) {
      setAuthMissing(true);
      return;
    }
    api<WorkspaceOut[]>("/workspaces")
      .then((ws) => {
        setWorkspaces(ws);
        const stored =
          typeof window !== "undefined"
            ? window.localStorage.getItem("qm_active_ws_id")
            : null;
        const pick = ws.find((w) => w.id === stored)?.id ?? ws[0]?.id ?? null;
        setActiveWs(pick);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeNode]);

  function pickWs(id: string) {
    setActiveWs(id);
    const name = workspaces.find((w) => w.id === id)?.name ?? "";
    if (typeof window !== "undefined") {
      window.localStorage.setItem("qm_active_ws_id", id);
      window.localStorage.setItem("qm_active_ws_name", name);
    }
  }

  if (authMissing) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16">
        <GlassPanel className="px-6 py-6 text-on-surface">
          You need to{" "}
          <a className="text-primary-container underline" href="/login">
            sign in
          </a>{" "}
          before chatting.
        </GlassPanel>
      </main>
    );
  }

  async function send(text?: string) {
    const userText = (text ?? input).trim();
    if (!userText || streaming) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { id: crypto.randomUUID(), role: "user", content: userText },
    ]);
    setStreaming(true);
    setActiveNode(null);

    let finalSpec: UISpec | null = null;
    let finalSql: string | null = null;
    let assistantId = crypto.randomUUID();

    try {
      await streamChat(
        { message: userText, session_id: sessionId, active_workspace_id: activeWs },
        (evt) => {
          if (evt.event === "session" && evt.data && typeof evt.data === "object") {
            const d = evt.data as { session_id?: string };
            if (d.session_id) setSessionId(d.session_id);
          } else if (evt.event === "node" && evt.data && typeof evt.data === "object") {
            const d = evt.data as { node?: string };
            if (d.node) setActiveNode(d.node);
          } else if (evt.event === "final" && evt.data && typeof evt.data === "object") {
            const d = evt.data as {
              ui_spec?: UISpec | null;
              sql?: string | null;
              assistant_message_id?: string;
            };
            finalSpec = d.ui_spec ?? null;
            finalSql = d.sql ?? null;
            if (d.assistant_message_id) assistantId = d.assistant_message_id;
          } else if (evt.event === "error") {
            const d = evt.data as { message?: string };
            finalSpec = {
              type: "text_only",
              body_md: `⚠️ ${d?.message ?? "Stream failed."}`,
            };
          }
        },
      );
    } catch (err) {
      finalSpec = {
        type: "text_only",
        body_md: `⚠️ ${err instanceof Error ? err.message : "Stream failed."}`,
      };
    } finally {
      setStreaming(false);
      setActiveNode(null);
      setMessages((m) => [
        ...m,
        { id: assistantId, role: "assistant", content: "", ui_spec: finalSpec, sql: finalSql },
      ]);
    }
  }

  const activeName = workspaces.find((w) => w.id === activeWs)?.name;

  return (
    <main className="mx-auto max-w-4xl px-container-margin py-5 flex flex-col h-[calc(100vh-61px)]">
      {/* Connected-DB context bar */}
      <div className="flex items-center justify-between gap-3 pb-4">
        <div className="flex items-center gap-2 text-on-surface">
          <span className="text-primary-container">
            <DatabaseIcon width={18} height={18} />
          </span>
          <span className="font-headline tracking-tight">
            {activeName ?? "No workspace"}
          </span>
          {activeWs ? (
            <span className="ml-2 flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-tertiary">
              <span className="qm-pulse-dot" /> Connected
            </span>
          ) : null}
        </div>
        {workspaces.length > 0 ? (
          <select
            value={activeWs ?? ""}
            onChange={(e) => pickWs(e.target.value)}
            className="rounded-lg border border-outline/25 bg-surface-container/60 px-3 py-1.5 font-mono text-sm text-on-surface outline-none focus:border-primary-container/60"
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id} className="bg-surface">
                {w.name}
              </option>
            ))}
          </select>
        ) : null}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-5 pr-1">
        {messages.length === 0 && !streaming ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-on-surface-variant">
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-primary-container/15 text-primary-container qm-glow mb-4">
              <SparkIcon width={26} height={26} />
            </span>
            <p className="font-headline text-xl text-on-surface">
              Ask your data anything
            </p>
            <p className="text-sm mt-1">
              Natural language in, read-only SQL + answers out.
            </p>
          </div>
        ) : null}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {streaming ? (
          <GlassPanel className="qm-gradient-border px-5 py-4 max-w-[85%]">
            <div className="flex items-center gap-2 font-mono text-label-caps uppercase text-primary-container mb-3">
              <SparkIcon width={16} height={16} /> Neural Response
            </div>
            <div className="text-on-surface-variant text-sm mb-2">
              {activeNode ? `Running ${activeNode.replace(/_/g, " ")}…` : "Analyzing your database…"}
            </div>
            <div className="h-1 w-40 rounded-full overflow-hidden bg-surface-container-high/60">
              <div className="qm-sweep h-full w-full" />
            </div>
          </GlassPanel>
        ) : null}
        <div ref={endRef} />
      </div>

      {/* Quick-reply chips */}
      <div className="flex flex-wrap gap-2 pt-4">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => send(s)}
            disabled={streaming}
            className="rounded-full border border-outline/25 bg-surface-container/40 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-on-surface-variant hover:border-primary-container/60 hover:text-primary-container transition disabled:opacity-40"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="mt-3 flex items-center gap-3 rounded-2xl border border-outline/20 bg-surface-container/50 backdrop-blur-xl px-4 py-2.5"
      >
        <span className="text-on-surface-variant">
          <TrendIcon width={20} height={20} />
        </span>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your data anything…"
          className="flex-1 bg-transparent text-on-surface placeholder:text-on-surface-variant/60 outline-none"
          disabled={streaming}
        />
        <button
          type="button"
          aria-label="Voice input"
          className="grid h-9 w-9 place-items-center rounded-lg text-on-surface-variant hover:text-on-surface transition"
          title="Voice input (not yet wired)"
        >
          <MicIcon />
        </button>
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          aria-label="Send"
          className="grid h-10 w-10 place-items-center rounded-xl bg-primary-container text-on-primary-container qm-glow disabled:opacity-40 disabled:shadow-none transition"
        >
          <SendIcon />
        </button>
      </form>
    </main>
  );
}
