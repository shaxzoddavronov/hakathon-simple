"use client";

import { useEffect, useRef, useState } from "react";

import { GlassPanel } from "@/components/GlassPanel";
import { MessageBubble } from "@/components/MessageBubble";
import { getToken, streamChat } from "@/lib/api";
import type { ChatMessage, UISpec } from "@/lib/types";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [authMissing, setAuthMissing] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setAuthMissing(!getToken());
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeNode]);

  if (authMissing) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16">
        <GlassPanel className="px-6 py-6 text-on-surface">
          You need to{" "}
          <a className="text-primary underline" href="/login">
            sign in
          </a>{" "}
          before chatting.
        </GlassPanel>
      </main>
    );
  }

  async function send() {
    if (!input.trim() || streaming) return;
    const userText = input.trim();
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
        { message: userText, session_id: sessionId, active_workspace_id: null },
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
        {
          id: assistantId,
          role: "assistant",
          content: "",
          ui_spec: finalSpec,
          sql: finalSql,
        },
      ]);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 flex flex-col h-screen">
      <header className="mb-4">
        <h1 className="font-headline text-2xl text-on-surface">Neural Chat</h1>
        <p className="text-on-surface-variant text-sm">
          Ask anything about your connected databases.
        </p>
      </header>

      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {streaming ? (
          <div className="text-on-surface-variant text-sm italic">
            {activeNode ? `running ${activeNode}…` : "thinking…"}
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="mt-4 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded-xl bg-surface-container-high/60 px-4 py-2 text-on-surface border border-outline/20 focus:outline-none focus:border-primary"
          disabled={streaming}
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="rounded-xl bg-primary-container text-on-primary-container px-4 py-2 font-semibold disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </main>
  );
}
