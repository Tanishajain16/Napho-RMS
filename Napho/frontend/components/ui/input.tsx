import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, onWheel, ...props }, ref) => {
    return (
      <input
        type={type}
        // Browsers change a focused number input's value on mouse-wheel scroll, silently
        // altering amounts (e.g. 500 -> 484) when the user scrolls the page. Blur instead,
        // so the wheel scrolls the page and the typed value stays as entered.
        onWheel={(e) => {
          if (type === "number" && document.activeElement === e.currentTarget) {
            e.currentTarget.blur()
          }
          onWheel?.(e)
        }}
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
