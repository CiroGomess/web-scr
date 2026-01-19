"use client";

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import CircularProgress from "@mui/material/CircularProgress";

type Props = {
  open: boolean;
  title?: string;
  message?: string;
};

function formatElapsed(totalSeconds: number) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;

  const pad = (n: number) => String(n).padStart(2, "0");
  if (hh > 0) return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
  return `${pad(mm)}:${pad(ss)}`;
}

export default function FullScreenProcessingOverlay({
  open,
  title = "Processamento em andamento",
  message = "Processando dados, aguarde...",
}: Props) {
  const [mounted, setMounted] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Zera e inicia o contador ao abrir; para ao fechar
  useEffect(() => {
    if (!open) {
      setElapsed(0);
      return;
    }

    const startedAt = Date.now();
    setElapsed(0);

    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [open]);

  const elapsedLabel = useMemo(() => formatElapsed(elapsed), [elapsed]);


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
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <p className="text-gray-900 font-semibold">{title}</p>

              {/* Contador */}
              <span className="shrink-0 text-xs font-semibold text-gray-700 bg-gray-100 rounded-full px-3 py-1">
                {elapsedLabel}
              </span>
            </div>

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
