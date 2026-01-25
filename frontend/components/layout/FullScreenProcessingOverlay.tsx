"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import { createPortal } from "react-dom";
import CircularProgress from "@mui/material/CircularProgress";
import services from "../../services/service";

type Props = {
  open: boolean;
  title?: string;
  message?: string;
  onLogsUpdate?: (logs: string[], progresso: any) => void;
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
  onLogsUpdate,
}: Props) {
  const [mounted, setMounted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [progresso, setProgresso] = useState<any>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Zera e inicia o contador ao abrir; para ao fechar
  useEffect(() => {
    if (!open) {
      setElapsed(0);
      setLogs([]);
      setProgresso(null);
      setCurrentSessionId(null);
      return;
    }

    // Limpa logs quando o overlay abre (novo processamento)
    setLogs([]);
    setProgresso(null);
    setCurrentSessionId(null);

    const startedAt = Date.now();
    setElapsed(0);

    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [open]);

  // Polling de logs - acumula logs ao invés de substituir
  useEffect(() => {
    if (!open) return;

    const fetchLogs = async () => {
      try {
        const result = await services("/processar/logs", { method: "GET" });
        if (result?.success && result?.data) {
          const newLogs = result.data.logs || [];
          const newProgresso = result.data.progresso || null;
          const newSessionId = result.data.session_id || null;
          
          // Se o session_id mudou ou é a primeira vez (currentSessionId é null), é um novo processamento
          if (newSessionId && newSessionId !== currentSessionId) {
            setCurrentSessionId(newSessionId);
            // Se há logs novos, usa eles; senão, mantém vazio (processamento ainda não começou)
            if (newLogs.length > 0) {
              setLogs(newLogs);  // Substitui completamente com os novos logs
            } else {
              setLogs([]);  // Garante que está vazio se não há logs ainda
            }
            setProgresso(newProgresso);
            return;
          }
          
          // Se é a mesma sessão (ou ainda não temos session_id), acumula logs normalmente
          if (newSessionId === currentSessionId || (currentSessionId === null && newSessionId)) {
            // Se recebeu um session_id pela primeira vez, atualiza
            if (currentSessionId === null && newSessionId) {
              setCurrentSessionId(newSessionId);
            }
            // Acumula logs: mantém os existentes e adiciona apenas os novos
            setLogs((prevLogs) => {
              // Se não há logs anteriores, usa os novos
              if (prevLogs.length === 0) {
                return newLogs;
              }
              
              // Se os novos logs têm mais itens, adiciona apenas os novos
              if (newLogs.length > prevLogs.length) {
                // Pega apenas os logs que ainda não temos (a partir do tamanho atual)
                const logsToAdd = newLogs.slice(prevLogs.length);
                return [...prevLogs, ...logsToAdd];
              }
              
              // Se os novos logs têm o mesmo tamanho ou menos, mas podem ter conteúdo diferente
              // Compara o último log para ver se há mudanças
              if (newLogs.length > 0 && prevLogs.length > 0) {
                const lastPrev = prevLogs[prevLogs.length - 1];
                const lastNew = newLogs[newLogs.length - 1];
                
                // Se o último log mudou, pode ter novos logs no meio
                // Nesse caso, substitui completamente para garantir consistência
                if (lastPrev !== lastNew) {
                  return newLogs;
                }
              }
              
              // Se os logs são os mesmos, mantém os anteriores
              return prevLogs;
            });
          }
          
          setProgresso(newProgresso);
          
          if (onLogsUpdate) {
            onLogsUpdate(newLogs, newProgresso);
          }
        }
      } catch (err) {
        console.error("Erro ao buscar logs:", err);
      }
    };

    // Busca logs imediatamente e depois a cada 2 segundos
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);

    return () => clearInterval(interval);
  }, [open, onLogsUpdate, currentSessionId]);

  // Auto-scroll para o final dos logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const elapsedLabel = useMemo(() => formatElapsed(elapsed), [elapsed]);
  
  const tempoEstimadoLabel = useMemo(() => {
    if (progresso?.tempo_estimado_restante_segundos) {
      return formatElapsed(progresso.tempo_estimado_restante_segundos);
    }
    return null;
  }, [progresso]);


  if (!open || !mounted) return null;

  const progressoPercentual = progresso?.total_produtos > 0 
    ? Math.round((progresso.itens_processados / progresso.total_produtos) * 100)
    : progresso?.total_fornecedores > 0
    ? Math.round((progresso.fornecedores_concluidos / progresso.total_fornecedores) * 100)
    : 0;

  return createPortal(
    <div
      className="fixed top-0 left-0 w-screen h-screen z-[99999] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop (pega a tela inteira mesmo) */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Card */}
      <div className="relative w-[92%] max-w-4xl bg-white rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.35)] p-6 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-4 mb-4">
          <CircularProgress size={28} />
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <p className="text-gray-900 font-semibold">{title}</p>

              {/* Contadores */}
              <div className="flex gap-2 shrink-0">
                <span className="text-xs font-semibold text-gray-700 bg-gray-100 rounded-full px-3 py-1">
                  {elapsedLabel}
                </span>
                {tempoEstimadoLabel && (
                  <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 rounded-full px-3 py-1">
                    ~{tempoEstimadoLabel}
                  </span>
                )}
              </div>
            </div>

            <p className="text-gray-600 text-sm mt-1 break-words">{message}</p>
          </div>
        </div>

        {/* Barra de Progresso */}
        {progresso && (
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>
                {progresso.total_produtos > 0 
                  ? `Produtos: ${progresso.itens_processados}/${progresso.total_produtos}`
                  : `Fornecedores: ${progresso.fornecedores_concluidos}/${progresso.total_fornecedores}`}
              </span>
              <span>{progressoPercentual}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progressoPercentual}%` }}
              />
            </div>
          </div>
        )}

        {/* Logs */}
        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          <div className="text-xs font-semibold text-gray-700 mb-2">Logs do Processamento:</div>
          <div className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-3 font-mono text-xs space-y-1 max-h-64">
            {logs.length === 0 ? (
              <div className="text-gray-400 italic">Aguardando logs...</div>
            ) : (
              logs.map((log, idx) => (
                <div 
                  key={idx} 
                  className={`${
                    log.includes("❌") || log.includes("Erro") || log.includes("Falha")
                      ? "text-red-600"
                      : log.includes("✅") || log.includes("SUCESSO")
                      ? "text-green-600"
                      : log.includes("⚠️")
                      ? "text-yellow-600"
                      : "text-gray-700"
                  }`}
                >
                  {log}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>

        <div className="mt-4 text-xs text-gray-500">
          Não feche a aba nem navegue para outra página até finalizar.
        </div>
      </div>
    </div>,
    document.body
  );
}
