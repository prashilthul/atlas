"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, X, Info } from "lucide-react";

export interface ToastMessage {
  id: string;
  type: "success" | "error" | "info";
  title: string;
  message?: string;
}

let toastListener: ((toast: ToastMessage) => void) | null = null;

export function showToast(type: "success" | "error" | "info", title: string, message?: string) {
  if (toastListener) {
    toastListener({
      id: `toast-${Date.now()}-${Math.random()}`,
      type,
      title,
      message,
    });
  }
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    toastListener = (newToast) => {
      setToasts((prev) => [...prev.slice(-4), newToast]);
    };
    return () => {
      toastListener = null;
    };
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onClose={() => removeToast(t.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onClose }: { toast: ToastMessage; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-lg transition-all animate-in fade-in slide-in-from-bottom-5 duration-200 ${
        toast.type === "success"
          ? "bg-slate-900 text-white border-slate-800"
          : toast.type === "error"
          ? "bg-rose-950 text-rose-50 border-rose-800"
          : "bg-slate-900 text-slate-50 border-slate-800"
      }`}
    >
      {toast.type === "success" && <CheckCircle2 className="size-4 text-emerald-400 shrink-0 mt-0.5" />}
      {toast.type === "error" && <AlertCircle className="size-4 text-rose-400 shrink-0 mt-0.5" />}
      {toast.type === "info" && <Info className="size-4 text-slate-300 shrink-0 mt-0.5" />}

      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold leading-snug">{toast.title}</p>
        {toast.message && <p className="text-[11px] opacity-80 mt-0.5 leading-relaxed">{toast.message}</p>}
      </div>

      <button
        onClick={onClose}
        className="shrink-0 p-1 text-slate-400 hover:text-white rounded-lg transition-colors"
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}
