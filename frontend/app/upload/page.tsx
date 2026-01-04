"use client";

import { useEffect, useState } from "react";
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
    setProcessMessage("Processando dados, aguarde...");

    try {
      const result = await services("/processar", { method: "POST" });

      // Se o seu services() não retorna success, ajuste aqui conforme seu padrão
      if (result?.success === false) {
        throw new Error(result?.data?.message || "Falha ao processar");
      }

      setProcessMessage("Processamento concluído com sucesso!");
      setTimeout(() => setProcessing(false), 800);
    } catch (err: any) {
      setProcessMessage("Ocorreu um erro no processamento.");
      setTimeout(() => setProcessing(false), 1200);
      alert(err?.message || "Erro ao processar dados");
    }
  };

  // Bloqueia scroll e impede fechar/refresh enquanto processa
  useEffect(() => {
    if (!processing) {
      document.body.style.overflow = "";
      return;
    }

    document.body.style.overflow = "hidden";

    const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", beforeUnloadHandler);

    return () => {
      window.removeEventListener("beforeunload", beforeUnloadHandler);
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
      />

      <div className="flex justify-center items-start mt-16 px-4">
        <div className="w-full max-w-xl bg-white rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.12)] p-8 animate-fadeIn">
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
