"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import CircularProgress from "@mui/material/CircularProgress";

type Props = {
  open: boolean;
  title?: string;
  message?: string;
};

export default function FullScreenProcessingOverlay({
  open,
  title = "Processamento em andamento",
  message = "Processando dados, aguarde...",
}: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!open || !mounted) return null;

  return createPortal(
    <div
      className="fixed top-0 left-0 w-screen h-screen z-[99999] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop (pega a tela inteira mesmo) */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Card */}
      <div className="relative w-[92%] max-w-lg bg-white rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.35)] p-6">
        <div className="flex items-center gap-4">
          <CircularProgress size={28} />
          <div className="min-w-0">
            <p className="text-gray-900 font-semibold">{title}</p>
            <p className="text-gray-600 text-sm mt-1 break-words">{message}</p>
          </div>
        </div>

        <div className="mt-5 text-xs text-gray-500">
          Não feche a aba nem navegue para outra página até finalizar.
        </div>
      </div>
    </div>,
    document.body
  );
}
