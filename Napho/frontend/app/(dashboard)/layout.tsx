"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import {
  LayoutDashboard,
  FileText,
  Plus,
  ClipboardCheck,
  CreditCard,
  Settings,
  LogOut,
  Bell,
  Menu,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  Users,
  LayoutList,
  GitBranch,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAuthStore } from "@/lib/auth"
import { useNotifications } from "@/hooks/use-notifications"
import { NotificationPanel } from "@/components/notifications/NotificationPanel"
import { ChatWidget } from "@/components/chat/ChatWidget"
import { cn } from "@/lib/utils"

const ALL_NAV = [
  { href: "/dashboard",   label: "Dashboard",    icon: LayoutDashboard, roles: ["all"] },
  { href: "/claims",      label: "My Claims",    icon: FileText,        roles: ["employee"] },
  { href: "/claims/new",  label: "New Claim",    icon: Plus,            roles: ["employee"] },
  { href: "/approvals",   label: "Review Queue", icon: ClipboardCheck,  roles: ["approver", "admin"] },
  { href: "/manager",     label: "Manager View", icon: LayoutList,      roles: ["approver", "admin"] },
  { href: "/payments",    label: "Payments",     icon: CreditCard,      roles: ["finance", "admin"] },
  { href: "/analytics",   label: "Analytics",    icon: BarChart3,       roles: ["admin"] },
  { href: "/admin/users",            label: "Users",           icon: Users,       roles: ["admin"] },
  { href: "/admin/approval-chains", label: "Approval Chains", icon: GitBranch,   roles: ["admin"] },
  { href: "/settings",    label: "Settings",     icon: Settings,        roles: ["all"] },
]

function useNavItems(roles: string[]) {
  return ALL_NAV.filter(
    (item) => item.roles.includes("all") || item.roles.some((r) => roles.includes(r))
  )
}

function NavItem({
  href,
  label,
  icon: Icon,
  active,
  collapsed,
}: {
  href: string
  label: string
  icon: React.ElementType
  active: boolean
  collapsed: boolean
}) {
  return (
    <Link href={href}>
      <div
        className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-150",
          active
            ? "bg-primary/10 text-primary border border-primary/20"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
          collapsed && "justify-center px-2"
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        {!collapsed && <span className="text-sm font-medium">{label}</span>}
      </div>
    </Link>
  )
}

function SidebarInner({
  collapsed,
  navItems,
  pathname,
  user,
  onLogout,
}: {
  collapsed: boolean
  navItems: typeof ALL_NAV
  pathname: string
  user: { name: string; roles: string[] }
  onLogout: () => void
}) {
  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div
        className={cn(
          "flex items-center gap-2.5 p-4 border-b border-border h-14 shrink-0",
          collapsed && "justify-center"
        )}
      >
        <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <span className="text-primary-foreground font-bold text-sm">N</span>
        </div>
        {!collapsed && (
          <span className="font-bold text-foreground tracking-tight">Napho RMS</span>
        )}
      </div>

      {/* Nav */}
      <ScrollArea className="flex-1 p-2">
        <nav className="space-y-0.5">
          {navItems.map((item) => (
            <NavItem
              key={item.href}
              {...item}
              active={
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href))
              }
              collapsed={collapsed}
            />
          ))}
        </nav>
      </ScrollArea>

      {/* User footer */}
      <div className={cn("p-3 border-t border-border shrink-0", collapsed && "flex justify-center")}>
        {!collapsed ? (
          <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-muted/50">
            <Avatar className="h-7 w-7 shrink-0">
              <AvatarFallback className="bg-primary/20 text-primary text-xs font-semibold">
                {user.name[0].toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate leading-none mb-0.5">
                {user.name}
              </p>
              <p className="text-[11px] text-muted-foreground capitalize leading-none">
                {user.roles[0]}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground shrink-0"
              onClick={onLogout}
            >
              <LogOut className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
            onClick={onLogout}
          >
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, isLoading, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showNotifs, setShowNotifs] = useState(false)
  const notifRef = useRef<HTMLDivElement>(null)

  const { data: notifData } = useNotifications()
  const unread = notifData?.unread_count ?? 0
  const navItems = useNavItems(user?.roles ?? [])

  // Close notif panel on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifs(false)
      }
    }
    if (showNotifs) document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [showNotifs])

  // Close mobile sidebar on route change
  useEffect(() => { setMobileOpen(false) }, [pathname])

  useEffect(() => {
    if (!isLoading && !user) router.push("/login")
  }, [user, isLoading, router])

  // Admins have no My Claims / New Claim pages — send them back if they open these URLs.
  // (Claim detail pages /claims/{id} stay reachable, e.g. from Review Queue / Payments.)
  const isAdminOnly = !!user && user.roles.includes("admin") && !user.roles.includes("employee")
  const onEmployeeOnlyPage =
    pathname === "/claims" || pathname === "/claims/new" || /^\/claims\/[^/]+\/edit$/.test(pathname)
  const blockPage = isAdminOnly && onEmployeeOnlyPage
  useEffect(() => {
    if (blockPage) router.replace("/dashboard")
  }, [blockPage, router])

  if (isLoading) return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  )

  if (!user || blockPage) return null

  const handleLogout = () => {
    logout()
    router.push("/login")
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <motion.aside
        animate={{ width: collapsed ? 64 : 240 }}
        transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
        className="hidden md:flex flex-col border-r border-border bg-card overflow-hidden shrink-0 relative"
      >
        <SidebarInner
          collapsed={collapsed}
          navItems={navItems}
          pathname={pathname}
          user={user}
          onLogout={handleLogout}
        />

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="absolute bottom-16 -right-3 z-20 flex items-center justify-center w-6 h-6 rounded-full bg-card border border-border hover:bg-accent transition-colors shadow-sm"
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          ) : (
            <ChevronLeft className="h-3 w-3 text-muted-foreground" />
          )}
        </button>
      </motion.aside>

      {/* Mobile Sidebar */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-60 p-0 bg-card border-border">
          <SidebarInner
            collapsed={false}
            navItems={navItems}
            pathname={pathname}
            user={user}
            onLogout={handleLogout}
          />
        </SheetContent>
      </Sheet>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="h-14 border-b border-border bg-card/50 backdrop-blur-sm flex items-center justify-between px-4 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="md:hidden h-8 w-8 p-0"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-4 w-4" />
          </Button>
          <div className="flex-1" />

          {/* Notification bell */}
          <div ref={notifRef} className="relative">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 relative"
              onClick={() => setShowNotifs((v) => !v)}
            >
              <Bell className="h-4 w-4" />
              {unread > 0 && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 500, damping: 20 }}
                  className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-primary text-primary-foreground text-[10px] flex items-center justify-center font-bold"
                >
                  {unread > 9 ? "9+" : unread}
                </motion.span>
              )}
            </Button>

            <AnimatePresence>
              {showNotifs && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  transition={{ duration: 0.18 }}
                  className="absolute right-0 top-10 z-50"
                >
                  <NotificationPanel onClose={() => setShowNotifs(false)} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <Avatar className="h-7 w-7 ml-3">
            <AvatarFallback className="bg-primary/20 text-primary text-xs font-semibold">
              {user.name[0].toUpperCase()}
            </AvatarFallback>
          </Avatar>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {children}
          </motion.div>
        </main>
      </div>

      <ChatWidget />
    </div>
  )
}
