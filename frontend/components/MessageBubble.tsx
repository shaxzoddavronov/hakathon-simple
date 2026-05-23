"use client";

import { CodeBlock } from "@/components/CodeBlock";
import { RenderSpec } from "@/components/RenderSpec";
import { cn } from "@/lib/cn";
import type { ChatMessage } from "@/lib/types";

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-primary-container/30 text-on-surface">
          {message.content}
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-2">
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
