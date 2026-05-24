"use client";

import { CodeBlock } from "@/components/CodeBlock";
import { RenderSpec } from "@/components/RenderSpec";
import { SparkIcon } from "@/components/icons";
import type { ChatMessage } from "@/lib/types";

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl border-l-2 border-primary-container/70 bg-primary-container/12 px-4 py-3 text-on-surface qm-glow">
          {message.content}
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-2xl qm-gradient-border bg-surface-container/30 backdrop-blur-xl p-5 space-y-3">
      <div className="flex items-center gap-2 font-mono text-label-caps uppercase text-primary-container">
        <SparkIcon width={16} height={16} /> Neural Response
      </div>
      {message.ui_spec ? (
        <RenderSpec spec={message.ui_spec} />
      ) : (
        <div className="text-on-surface-variant italic">No response.</div>
      )}
      {message.sql ? (
        <CodeBlock language="sql" code={message.sql} collapsible />
      ) : null}
    </div>
  );
}
