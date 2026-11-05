"use client"

import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { Bot, X, Send, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useChat } from "@/hooks/use-chat"
import { useAuthStore } from "@/lib/auth"
import { cn } from "@/lib/utils"

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 mb-3">
      <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
        <Bot className="h-3 w-3 text-primary" />
      </div>
      <div className="bg-muted/60 border border-border/40 rounded-2xl rounded-bl-sm px-3.5 py-2.5">
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60"
              animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
              transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.18, ease: "easeInOut" }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function getGreeting(roles: string[]): string {
  if (roles.includes("admin")) return "Hi! I'm Napho AI. As an admin, I can help you with analytics, user management, claim overviews, and more. What would you like to know?"
  if (roles.includes("finance")) return "Hi! I'm Napho AI. I can help you with payment processing, financial reports, and claim approvals. How can I assist?"
  if (roles.includes("approver")) return "Hi! I'm Napho AI. I can help you review pending claims, check approval queues, and understand claim details. What do you need?"
  return "Hi! I'm Napho AI. I can help you file claims, check their status, and understand your reimbursements. How can I help?"
}

export function ChatWidget() {
  const { user } = useAuthStore()
  const { messages, sendMessage, isLoading, setMessages } = useChat()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const greeted = useRef(false)

  // Inject greeting on first open
  useEffect(() => {
    if (open && !greeted.current && user) {
      greeted.current = true
      setMessages([{ role: "assistant", content: getGreeting(user.roles) }])
    }
  }, [open, user, setMessages])

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isLoading])

  // Focus input when panel opens
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 150)
  }, [open])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput("")
    sendMessage(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.95 }}
            transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
            className="w-80 sm:w-96 h-[500px] bg-card border border-border/60 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center gap-2.5 px-4 py-3 border-b border-border/50 bg-card shrink-0">
              <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shrink-0">
                <Sparkles className="h-4 w-4 text-primary-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground leading-none mb-0.5">Napho AI</p>
                <p className="text-[11px] text-muted-foreground leading-none">Ask me anything</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground shrink-0"
                onClick={() => setOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 px-3 py-3">
              <div className="space-y-1">
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18 }}
                    className={cn(
                      "flex items-end gap-2 mb-3",
                      msg.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    {msg.role === "assistant" && (
                      <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center shrink-0 mb-0.5">
                        <Bot className="h-3 w-3 text-primary" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground rounded-br-sm"
                          : "bg-muted/60 text-foreground border border-border/40 rounded-bl-sm"
                      )}
                    >
                      {msg.content}
                    </div>
                  </motion.div>
                ))}

                {isLoading && <TypingIndicator />}
                <div ref={bottomRef} />
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="px-3 py-3 border-t border-border/50 bg-card shrink-0">
              <div className="flex items-center gap-2">
                <Input
                  ref={inputRef}
                  placeholder="Message Napho AI…"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  className="h-9 text-sm bg-muted/40 border-border/50 focus-visible:ring-primary/40"
                />
                <Button
                  size="sm"
                  className="h-9 w-9 p-0 shrink-0"
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                >
                  <Send className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating button */}
      <motion.button
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.94 }}
        onClick={() => setOpen((v) => !v)}
        className="w-13 h-13 rounded-full bg-primary text-primary-foreground shadow-lg hover:shadow-primary/30 flex items-center justify-center transition-shadow"
        style={{ width: 52, height: 52 }}
        aria-label="Open Napho AI chat"
      >
        <AnimatePresence mode="wait" initial={false}>
          {open ? (
            <motion.span
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <X className="h-5 w-5" />
            </motion.span>
          ) : (
            <motion.span
              key="bot"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <Bot className="h-5 w-5" />
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  )
}
