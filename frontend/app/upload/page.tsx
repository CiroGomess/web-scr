"use client";

import { useEffect, useState, useRef } from "react";
import services from "../../services/service";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import SettingsIcon from "@mui/icons-material/Settings";

import FullScreenProcessingOverlay from "../../components/layout/FullScreenProcessingOverlay";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showProcess, setShowProcess] = useState(false);

  const [processing, setProcessing] = useState(false);
  const [processMessage, setProcessMessage] = useState("Processando dados, aguarde...");
  
  // Ref para manter referência do handler beforeunload
  const beforeUnloadHandlerRef = useRef<((event: BeforeUnloadEvent) => void) | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const result = await services("/upload", {
        method: "POST",
        data: formData,
      });

      if (result.success) {
        setShowProcess(true);
      } else {
        alert(result.data?.message || "Erro ao enviar arquivo");
      }
    } catch (err: any) {
      alert(err?.message || "Erro inesperado ao enviar arquivo");
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async () => {
    if (processing) return;

    setProcessing(true);
    setProcessMessage("Iniciando processamento...");

    try {
      const result = await services("/processar", { method: "POST" });

      // Verifica se a requisição foi aceita (202) ou se houve erro
      if (result?.status === 202 || (result?.success && result?.data?.status === "processing")) {
        // Processamento iniciado em background - inicia polling
        setProcessMessage("Processamento iniciado. Acompanhe o progresso abaixo...");
        
        // Polling para verificar status do processamento
        const checkStatus = async () => {
          try {
            const statusResult = await services("/processar/status", { method: "GET" });
            
            if (statusResult?.success && statusResult?.data?.status === "completed") {
              // Processamento concluído!
              setProcessMessage("Processamento concluído com sucesso! Redirecionando...");
              
              setTimeout(() => {
                // Remove handler beforeunload ANTES de setar processing como false
                if (beforeUnloadHandlerRef.current) {
                  window.removeEventListener("beforeunload", beforeUnloadHandlerRef.current);
                  beforeUnloadHandlerRef.current = null;
                }
                window.onbeforeunload = null;
                
                // Agora seta processing como false (isso também remove o handler via useEffect)
                setProcessing(false);
                
                // Delay para garantir que o useEffect executou e tudo foi limpo
                setTimeout(() => {
                  // Verifica novamente antes de redirecionar (garantia extra)
                  window.onbeforeunload = null;
                  // Usa replace ao invés de href para evitar trigger do beforeunload
                  window.location.replace("/consulta");
                }, 300);
              }, 2000);
            } else if (statusResult?.data?.status === "processing") {
              // Ainda processando - continua verificando
              setTimeout(checkStatus, 5000); // Verifica a cada 5 segundos
            } else if (statusResult?.data?.status === "error") {
              // Erro no status
              setProcessMessage("Erro ao verificar status do processamento.");
              setTimeout(() => setProcessing(false), 3000);
            }
          } catch (err: any) {
            console.error("Erro ao verificar status:", err);
            // Continua tentando mesmo em caso de erro temporário
            setTimeout(checkStatus, 10000); // Tenta novamente em 10 segundos
          }
        };
        
        // Inicia o polling após 3 segundos (dá tempo para o processamento iniciar)
        setTimeout(checkStatus, 3000);
        
      } else if (result?.success === false) {
        throw new Error(result?.data?.message || result?.data?.error || "Falha ao iniciar processamento");
      } else {
        // Resposta inesperada, mas assume sucesso
        setProcessMessage("Processamento iniciado com sucesso!");
        setTimeout(() => setProcessing(false), 3000);
      }
    } catch (err: any) {
      setProcessMessage("Ocorreu um erro ao iniciar o processamento.");
      setTimeout(() => setProcessing(false), 2000);
      alert(err?.message || "Erro ao processar dados");
    }
  };

  // Bloqueia scroll e impede fechar/refresh enquanto processa
  useEffect(() => {
    if (!processing) {
      document.body.style.overflow = "";
      // Remove handler beforeunload quando processing é false
      if (beforeUnloadHandlerRef.current) {
        window.removeEventListener("beforeunload", beforeUnloadHandlerRef.current);
        beforeUnloadHandlerRef.current = null;
      }
      window.onbeforeunload = null;
      return;
    }

    document.body.style.overflow = "hidden";

    // Cria o handler e armazena na ref
    const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    
    beforeUnloadHandlerRef.current = beforeUnloadHandler;
    window.addEventListener("beforeunload", beforeUnloadHandler);

    return () => {
      if (beforeUnloadHandlerRef.current) {
        window.removeEventListener("beforeunload", beforeUnloadHandlerRef.current);
        beforeUnloadHandlerRef.current = null;
      }
      window.onbeforeunload = null;
      document.body.style.overflow = "";
    };
  }, [processing]);

  return (
    <>
      {/* Overlay Fullscreen REAL (cobre sidebar + header + tudo) */}
      <FullScreenProcessingOverlay
        open={processing}
        title="Processamento em andamento"
        message={processMessage}
        onLogsUpdate={(logs, progresso) => {
          // Callback opcional para atualizações de logs
          // Pode ser usado para atualizar a mensagem baseada no progresso
        }}
      />

      <div className="flex justify-center items-start mt-16 px-4 w-full max-w-full overflow-x-hidden">
        <div className="w-full max-w-xl bg-white rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.12)] p-6 md:p-8 animate-fadeIn">
          <h2 className="text-2xl font-semibold text-gray-900 text-center mb-6">
            Upload de Arquivo XLSX
          </h2>

          <label
            className={`flex flex-col items-center justify-center text-center 
              border-2 border-dashed rounded-xl p-10 cursor-pointer transition
              ${
                file
                  ? "border-indigo-500 bg-indigo-50"
                  : "border-indigo-400 bg-indigo-50 hover:bg-indigo-100"
              }`}
          >
            <CloudUploadIcon className="text-indigo-600" sx={{ fontSize: 42 }} />

            <p className="mt-4 text-gray-700">
              Clique aqui ou arraste um arquivo <strong>.xlsx</strong>
            </p>

            <p className="mt-2 text-sm text-gray-500 flex items-center gap-1">
              <InfoOutlinedIcon sx={{ fontSize: 16 }} />
              Arquivos Excel (.xlsx) até 10MB
            </p>

            <input
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={handleFileChange}
              disabled={uploading || processing}
            />
          </label>

          {file && (
            <div className="mt-4 text-sm bg-gray-50 p-3 rounded border-l-4 border-indigo-500">
              Selecionado: <strong>{file.name}</strong>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!file || uploading || processing}
            className="w-full mt-6 flex items-center justify-center gap-2
              bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-lg
              font-medium transition disabled:bg-gray-400"
          >
            <CloudUploadIcon />
            {uploading ? "Enviando..." : "Enviar Arquivo"}
          </button>

          {showProcess && (
            <button
              onClick={handleProcess}
              disabled={processing}
              className="w-full mt-4 flex items-center justify-center gap-2
                bg-emerald-600 hover:bg-emerald-700 text-white py-3 rounded-lg
                font-medium transition animate-slideUp disabled:bg-gray-400"
            >
              <SettingsIcon />
              {processing ? "Processando..." : "Processar Dados"}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
