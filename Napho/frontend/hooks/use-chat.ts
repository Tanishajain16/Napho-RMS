import { useState } from "react"
import { api, getApiError } from "@/lib/api"
import type { ChatMessage } from "@/lib/types"

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const sendMessage = async (content: string) => {
    const newMessages = [...messages, { role: "user" as const, content }]
    setMessages(newMessages)
    setIsLoading(true)
    try {
      const { data } = await api.post("/chat", {
        message: content,
        conversation_history: messages.slice(-8),
      })
      setMessages([...newMessages, { role: "assistant" as const, content: data.reply }])
    } catch (err: unknown) {
      setMessages([
        ...newMessages,
        {
          role: "assistant" as const,
          content: `Sorry — ${getApiError(err, "I encountered an error. Please try again.")}`,
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return { messages, sendMessage, isLoading, setMessages }
}
