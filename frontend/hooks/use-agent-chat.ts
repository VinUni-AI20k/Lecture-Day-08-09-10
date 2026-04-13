"use client"

import * as React from "react"
import { toast } from "sonner"
import { useShallow } from "zustand/react/shallow"

import { iterateAgentEventsFromResponse } from "@/lib/agent/parse-sse"
import { useAssistantStore } from "@/stores/assistant-store"

export type { TraceRow, UiMessage } from "@/lib/types/chat-ui"

export function useAgentChat() {
  const {
    messages,
    streamingText,
    loading,
    traceRows,
    sources,
    pipeline,
    lastTraceId,
    grounded,
  } = useAssistantStore(
    useShallow((s) => ({
      messages: s.messages,
      streamingText: s.streamingText,
      loading: s.loading,
      traceRows: s.traceRows,
      sources: s.sources,
      pipeline: s.pipeline,
      lastTraceId: s.lastTraceId,
      grounded: s.grounded,
    }))
  )

  const abortRef = React.useRef<AbortController | null>(null)

  const stop = React.useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    const snap = useAssistantStore.getState().streamingText
    useAssistantStore.getState().pushStoppedAssistant(snap)
  }, [])

  const send = React.useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return
    if (useAssistantStore.getState().loading) return

    useAssistantStore.getState().beginSend(trimmed)

    const ac = new AbortController()
    abortRef.current = ac

    const nextMessages = useAssistantStore.getState().messages.map(
      ({ role, content }) => ({ role, content })
    )

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages }),
        signal: ac.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(
          typeof err?.error === "string" ? err.error : res.statusText
        )
      }

      let buffer = ""

      for await (const ev of iterateAgentEventsFromResponse(res)) {
        switch (ev.type) {
          case "step_started":
            useAssistantStore.getState().pushTraceRow({
              kind: "step",
              stepId: ev.stepId,
              label: ev.label,
              node: ev.node,
            })
            break
          case "route_decision":
            useAssistantStore.getState().pushTraceRow({
              kind: "route",
              route: ev.route,
              reason: ev.reason,
            })
            break
          case "retrieval_result":
            useAssistantStore.getState().setSources(ev.chunks)
            break
          case "token":
            buffer += ev.delta
            useAssistantStore.getState().setStreamingText(buffer)
            break
          case "pipeline_signal":
            useAssistantStore.getState().setPipeline(ev.metrics)
            break
          case "error":
            toast.error(ev.message)
            break
          case "done":
            useAssistantStore.getState().setLastTraceId(ev.traceId)
            break
        }
      }

      if (buffer.trim()) {
        useAssistantStore.getState().pushAssistantMessage(buffer)
      } else {
        useAssistantStore.getState().setLoading(false)
        useAssistantStore.getState().clearStreaming()
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        return
      }
      const msg = e instanceof Error ? e.message : "Lỗi không xác định"
      toast.error(msg)
      useAssistantStore.getState().setLoading(false)
      useAssistantStore.getState().clearStreaming()
    } finally {
      abortRef.current = null
    }
  }, [])

  const copyTraceJson = React.useCallback(async () => {
    const { lastTraceId, traceRows, sources, pipeline, grounded } =
      useAssistantStore.getState()
    const payload = {
      traceId: lastTraceId,
      traceRows,
      sources,
      pipeline,
      grounded,
    }
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
      toast.success("Đã copy trace JSON")
    } catch {
      toast.error("Không copy được")
    }
  }, [])

  const clearSession = React.useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    useAssistantStore.getState().clearSession()
    toast.message("Đã bắt đầu cuộc trò chuyện mới")
  }, [])

  return {
    messages,
    streamingText,
    loading,
    traceRows,
    sources,
    pipeline,
    lastTraceId,
    grounded,
    send,
    stop,
    copyTraceJson,
    clearSession,
  }
}
