"use client";

import { useState } from "react";
import services from "../../services/service";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import SettingsIcon from "@mui/icons-material/Settings";

export default function UploadPage() {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [showProcess, setShowProcess] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.length) return;
        setFile(e.target.files[0]);
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
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

        setUploading(false);
    };

    return (
        <div className="flex justify-center items-start mt-16 px-4">
            {/* CARD */}
            <div className="w-full max-w-xl bg-white rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.12)] p-8 animate-fadeIn">
                <h2 className="text-2xl font-semibold text-gray-900 text-center mb-6">
                    Upload de Arquivo XLSX
                </h2>

                {/* DROPZONE */}
                <label
                    className={`flex flex-col items-center justify-center text-center 
          border-2 border-dashed rounded-xl p-10 cursor-pointer transition
          ${file
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
                    />
                </label>

                {/* FILE NAME */}
                {file && (
                    <div className="mt-4 text-sm bg-gray-50 p-3 rounded border-l-4 border-indigo-500">
                        Selecionado: <strong>{file.name}</strong>
                    </div>
                )}

                {/* UPLOAD BUTTON */}
                <button
                    onClick={handleUpload}
                    disabled={!file || uploading}
                    className="w-full mt-6 flex items-center justify-center gap-2
          bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-lg
          font-medium transition disabled:bg-gray-400"
                >
                    <CloudUploadIcon />
                    {uploading ? "Enviando..." : "Enviar Arquivo"}
                </button>

                {/* PROCESS BUTTON */}
                {showProcess && (
                    <button
                        onClick={() => services("/processar", { method: "POST" })}
                        className="w-full mt-4 flex items-center justify-center gap-2
            bg-emerald-600 hover:bg-emerald-700 text-white py-3 rounded-lg
            font-medium transition animate-slideUp"
                    >
                        <SettingsIcon />
                        Processar Dados
                    </button>
                )}
            </div>
        </div>
    );
}
