"use client";

import { useEffect } from "react";

export function SoonToast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2400);
    return () => clearTimeout(t);
  }, [message, onDone]);

  return (
    <div
      role="status"
      aria-live="polite"
      className="soon-toast fixed left-1/2 -translate-x-1/2 bottom-8 z-50 px-5 py-3 rounded-2xl text-sm font-bold text-white"
      style={{
        background: "linear-gradient(90deg,#F5B544,#C2820B)",
        boxShadow: "0 14px 30px -10px rgba(194,130,11,.55)",
      }}
    >
      {message}
    </div>
  );
}
