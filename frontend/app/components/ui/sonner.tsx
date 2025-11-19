"use client";

import { useTheme } from "next-themes";
import { Toaster as Sonner, ToasterProps } from "sonner";

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme();

  // Get default position based on props or fallback to bottom-right
  const defaultPosition = props.position || "bottom-right";

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      position={defaultPosition}
      expand={false}
      visibleToasts={5}
      gap={12}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
        } as React.CSSProperties
      }
      toastOptions={{
        style: {
          opacity: 1,
        },
        classNames: {
          toast: "opacity-100",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
