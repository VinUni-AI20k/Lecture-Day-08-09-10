import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type { PipelineMetrics, RetrievalChunk } from "@/lib/types/agent-events"
import type { TraceRow, UiMessage } from "@/lib/types/chat-ui"

function newId() {
  return `m_${Math.random().toString(36).slice(2, 11)}`
}

/** Trace / RAG / pipeline slice — không gồm streamingText (tránh trùng key khi spread). */
function emptyRunFields() {
  return {
    traceRows: [] as TraceRow[],
    sources: [] as RetrievalChunk[],
    pipeline: null as PipelineMetrics | null,
    lastTraceId: undefined as string | undefined,
    grounded: null as boolean | null,
  }
}

export type AssistantState = {
  messages: UiMessage[]
  streamingText: string
  loading: boolean
} & ReturnType<typeof emptyRunFields>

type AssistantActions = {
  beginSend: (userContent: string) => void
  setStreamingText: (text: string) => void
  setLoading: (loading: boolean) => void
  pushTraceRow: (row: TraceRow) => void
  setSources: (chunks: RetrievalChunk[]) => void
  setPipeline: (metrics: PipelineMetrics | null) => void
  setGrounded: (grounded: boolean | null) => void
  setLastTraceId: (id: string | undefined) => void
  pushAssistantMessage: (content: string) => void
  pushStoppedAssistant: (streamingSnapshot: string) => void
  clearStreaming: () => void
  clearSession: () => void
}

export type AssistantStore = AssistantState & AssistantActions

const initialRun: AssistantState = {
  messages: [],
  streamingText: "",
  loading: false,
  ...emptyRunFields(),
}

export const useAssistantStore = create<AssistantStore>()(
  persist(
    (set, _get) => ({
      ...initialRun,

      beginSend: (userContent) => {
        const msg: UiMessage = {
          id: newId(),
          role: "user",
          content: userContent,
        }
        set({
          messages: [..._get().messages, msg],
          streamingText: "",
          loading: true,
          ...emptyRunFields(),
        })
      },

      setStreamingText: (text) => set({ streamingText: text }),

      setLoading: (loading) => set({ loading }),

      pushTraceRow: (row) =>
        set((s) => ({ traceRows: [...s.traceRows, row] })),

      setSources: (chunks) =>
        set({
          sources: chunks,
          grounded: chunks.length > 0,
        }),

      setPipeline: (metrics) => set({ pipeline: metrics }),

      setGrounded: (grounded) => set({ grounded }),

      setLastTraceId: (id) => set({ lastTraceId: id }),

      pushAssistantMessage: (content) =>
        set((s) => ({
          messages: [
            ...s.messages,
            { id: newId(), role: "assistant", content },
          ],
          streamingText: "",
          loading: false,
        })),

      pushStoppedAssistant: (streamingSnapshot) =>
        set((s) => {
          const trimmed = streamingSnapshot.trim()
          const tail = trimmed
            ? `${trimmed}\n\n*(Phản hồi đã dừng theo yêu cầu.)*`
            : ""
          return {
            messages: tail
              ? [
                  ...s.messages,
                  { id: newId(), role: "assistant", content: tail },
                ]
              : s.messages,
            streamingText: "",
            loading: false,
          }
        }),

      clearStreaming: () => set({ streamingText: "" }),

      clearSession: () =>
        set({
          messages: [],
          streamingText: "",
          loading: false,
          ...emptyRunFields(),
        }),
    }),
    {
      name: "assistant-chat-session",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (s) => ({ messages: s.messages }),
      skipHydration: true,
      version: 1,
    }
  )
)
