"use client"

import { formatDistanceToNow } from "date-fns"
import { Check, Bell, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card } from "@/components/ui/card"
import { useNotifications, useMarkAllRead } from "@/hooks/use-notifications"
import { cn } from "@/lib/utils"

export function NotificationPanel({ onClose }: { onClose: () => void }) {
  const { data } = useNotifications()
  const markAll = useMarkAllRead()
  const items = data?.items ?? []
  const unread = data?.unread_count ?? 0

  return (
    <Card className="w-80 border-border/60 shadow-2xl shadow-black/60 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-semibold">Notifications</span>
          {unread > 0 && (
            <span className="inline-flex items-center justify-center h-4 min-w-4 rounded-full bg-primary text-primary-foreground text-[10px] font-bold px-1">
              {unread}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {unread > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs text-muted-foreground hover:text-foreground px-2"
              onClick={() => markAll.mutate()}
              disabled={markAll.isPending}
            >
              <Check className="h-3 w-3 mr-1" />
              Mark all read
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
            onClick={onClose}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <ScrollArea className="h-80">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-10 text-muted-foreground">
            <Bell className="h-8 w-8 mb-2 opacity-25" />
            <p className="text-sm font-medium">All caught up!</p>
            <p className="text-xs opacity-60 mt-0.5">No new notifications</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {items.map((n) => (
              <div
                key={n.id}
                className={cn(
                  "px-4 py-3 transition-colors cursor-pointer hover:bg-accent/50",
                  !n.is_read && "bg-primary/5 border-l-2 border-l-primary"
                )}
              >
                <p
                  className={cn(
                    "text-sm leading-snug",
                    !n.is_read ? "text-foreground font-medium" : "text-muted-foreground"
                  )}
                >
                  {n.title}
                </p>
                {n.body && (
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.body}</p>
                )}
                <p className="text-[10px] text-muted-foreground/50 mt-1.5">
                  {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                </p>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </Card>
  )
}
