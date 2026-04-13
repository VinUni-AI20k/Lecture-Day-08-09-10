"use client";

import * as React from "react";
import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop?: () => void;
  loading: boolean;
  disabled?: boolean;
  className?: string;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  onStop,
  loading,
  disabled,
  className,
}: Props) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [value]);

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading && value.trim()) onSend();
    }
  }

  return (
    <div
      className={cn(
        "flex items-end gap-2 rounded-2xl border border-input bg-card px-4 py-3 shadow-sm",
        "transition-all duration-200",
        "focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20",
        disabled && "opacity-60",
        className
      )}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Đặt câu hỏi… (Enter để gửi, Shift+Enter xuống dòng)"
        rows={1}
        disabled={disabled || loading}
        className="flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50 min-h-[36px] max-h-[200px] leading-relaxed py-0.5 font-medium"
      />

      {loading ? (
        <Button
          type="button"
          size="icon"
          variant="destructive"
          onClick={onStop}
          className="h-9 w-9 shrink-0 rounded-xl shadow-sm"
          aria-label="Dừng tạo câu trả lời"
          title="Dừng"
        >
          <Square className="h-3.5 w-3.5 fill-current" />
        </Button>
      ) : (
        <Button
          type="button"
          size="icon"
          onClick={onSend}
          disabled={!value.trim() || disabled}
          className="h-9 w-9 shrink-0 rounded-xl shadow-sm"
          style={{ background: "var(--gradient-primary)" }}
          aria-label="Gửi"
        >
          <Send className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
