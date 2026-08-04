"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

interface ConfirmModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "destructive" | "default";
  onConfirm: () => void;
}

export function ConfirmModal({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "destructive",
  onConfirm,
}: ConfirmModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md w-full p-5 bg-white border border-slate-200 shadow-xl rounded-2xl">
        <DialogHeader className="space-y-2">
          <div className="flex items-center gap-2 text-rose-600 font-bold text-sm">
            <div className="size-8 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center shrink-0">
              <AlertTriangle className="size-4 text-rose-600" />
            </div>
            <DialogTitle className="text-sm font-bold text-slate-900 leading-snug">
              {title}
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs leading-relaxed text-slate-600 pt-1">
            {description}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100 mt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="h-8 px-3 text-xs text-slate-700 border-slate-300 hover:bg-slate-50"
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
            className={`h-8 px-3 text-xs font-semibold shadow-xs ${
              variant === "destructive"
                ? "bg-rose-600 hover:bg-rose-700 text-white"
                : "bg-slate-900 hover:bg-slate-800 text-white"
            }`}
          >
            {confirmText}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
