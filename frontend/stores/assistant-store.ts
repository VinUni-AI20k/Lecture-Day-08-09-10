import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import type {
  ConfidenceLevel,
  PipelineMetrics,
  RetrievalChunk,
} from "@/lib/types/agent-events"
import type { EmailDraftSnapshot, TraceRow, UiMessage } from "@/lib/types/chat-ui"

function emptyUiEphemeral() {
  return {
    answerConfidence: null as ConfidenceLevel | null,
    lastError: null as string | null,
  }
}

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
  /** Một dòng trạng thái cho luồng đang chạy (SSE). */
  activityLabel: string | null
} & ReturnType<typeof emptyRunFields> &
  ReturnType<typeof emptyUiEphemeral>

type AssistantActions = {
  beginSend: (userContent: string) => void
  setStreamingText: (text: string) => void
  setLoading: (loading: boolean) => void
  setActivityLabel: (label: string | null) => void
  pushTraceRow: (row: TraceRow) => void
  setSources: (chunks: RetrievalChunk[]) => void
  setPipeline: (metrics: PipelineMetrics | null) => void
  setGrounded: (grounded: boolean | null) => void
  setLastTraceId: (id: string | undefined) => void
  pushAssistantMessage: (
    content: string,
    meta?: {
      sourcesUsed?: RetrievalChunk[]
      routeKey?: string
      confidenceLevel?: ConfidenceLevel
      emailDraft?: EmailDraftSnapshot
    }
  ) => void
  pushStoppedAssistant: (streamingSnapshot: string) => void
  clearStreaming: () => void
  clearSession: () => void
  setAnswerConfidence: (level: ConfidenceLevel | null) => void
  setLastError: (message: string | null) => void
  /** Cập nhật trạng thái gửi email (demo HIL). */
  setEmailDraftStatus: (
    messageId: string,
    status: EmailDraftSnapshot["sendStatus"]
  ) => void
  /** Chuẩn bị state cho lần gọi lại sau lỗi (không thêm tin nhắn user). */
  beginRetrySend: () => void
}

export type AssistantStore = AssistantState & AssistantActions

const initialRun: AssistantState = {
  messages: [],
  streamingText: "",
  loading: false,
  activityLabel: null,
  ...emptyRunFields(),
  ...emptyUiEphemeral(),
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
          activityLabel: "Đang gửi câu hỏi…",
          ...emptyRunFields(),
          ...emptyUiEphemeral(),
        })
      },

      setStreamingText: (text) => set({ streamingText: text }),

      setLoading: (loading) => set({ loading }),

      setActivityLabel: (label) => set({ activityLabel: label }),

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

      pushAssistantMessage: (content, meta) =>
        set((s) => ({
          messages: [
            ...s.messages,
            {
              id: newId(),
              role: "assistant",
              content,
              ...(meta?.sourcesUsed?.length
                ? { sourcesUsed: meta.sourcesUsed }
                : {}),
              ...(meta?.routeKey ? { routeKey: meta.routeKey } : {}),
              ...(meta?.confidenceLevel
                ? { confidenceLevel: meta.confidenceLevel }
                : {}),
              ...(meta?.emailDraft ? { emailDraft: meta.emailDraft } : {}),
            },
          ],
          streamingText: "",
          loading: false,
          activityLabel: null,
          answerConfidence: null,
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
            activityLabel: null,
            answerConfidence: null,
          }
        }),

      clearStreaming: () => set({ streamingText: "" }),

      clearSession: () =>
        set({
          messages: [],
          streamingText: "",
          loading: false,
          activityLabel: null,
          ...emptyRunFields(),
          ...emptyUiEphemeral(),
        }),

      setAnswerConfidence: (level) => set({ answerConfidence: level }),

      setLastError: (message) => set({ lastError: message }),

      setEmailDraftStatus: (messageId, status) =>
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== messageId || !m.emailDraft) return m
            return {
              ...m,
              emailDraft: { ...m.emailDraft, sendStatus: status },
            }
          }),
        })),

      beginRetrySend: () =>
        set({
          ...emptyRunFields(),
          ...emptyUiEphemeral(),
          streamingText: "",
          loading: true,
          activityLabel: "Đang thử lại…",
          lastError: null,
        }),
    }),
    {
      name: "assistant-chat-session",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (s) => ({ messages: s.messages }),
      skipHydration: true,
      version: 2,
    }
  )
)
