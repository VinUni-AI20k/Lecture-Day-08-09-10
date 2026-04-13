"use client"

import * as React from "react"

import { useAssistantStore } from "@/stores/assistant-store"

/**
 * sessionStorage rehydration for persisted messages (client-only).
 * Must run once after mount to avoid SSR/client mismatch.
 */
export function AssistantStoreHydration() {
  React.useEffect(() => {
    void useAssistantStore.persist.rehydrate()
  }, [])
  return null
}
