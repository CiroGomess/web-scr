"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";


import services from "../../services/service";

// IMPORT DA LOGO (pasta raiz: /assets/logo.png)
// Se este arquivo estiver em: frontend/app/login/page.tsx
// o caminho costuma ser: ../../../assets/logo.png
import logo from "../../assets/logo.png";

import {
  LockOutlined,
  EmailOutlined,
  Visibility,
  VisibilityOff,
  LoginOutlined,
} from "@mui/icons-material";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const brandColor = "#255CA1";

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      console.log("Tentando logar com:", email);

      const result = await services("/auth/login", {
        method: "POST",
        data: { email: email, senha: password },
      });

      console.log("Resposta do Login:", result);

      if (result.success && result.data && result.data.token) {
        localStorage.setItem("token", result.data.token);

        if (result.data.user?.email) {
          localStorage.setItem("user_email", result.data.user.email);
        }

        console.log("Login sucesso! Redirecionando...");
        router.push("/upload");
      } else {
        setError(result.data?.message || "E-mail ou senha incorretos.");
      }
    } catch (err) {
      console.error("Erro no front:", err);
      setError("Erro de conexão. Verifique se o backend está rodando.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 relative overflow-hidden p-4">
      {/* Efeito de fundo (Glow Roxo) */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[500px] opacity-30 blur-[100px]"
        style={{
          background: `radial-gradient(circle, ${brandColor} 0%, rgba(0,0,0,0) 70%)`,
        }}
      />

      {/* Card de Login Glassmorphism */}
      <div className="relative z-10 bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden p-8 sm:p-10">
        {/* Cabeçalho / Branding */}
        <div className="text-center mb-8">
          <div className="mx-auto mb-6 flex items-center justify-center">
            <img
              src={logo.src}
              alt="Logo"
              width={600}
              height={600}
              style={{
                width: 600,
                height: 100,
                objectFit: "contain",
              }}
            />
          </div>



          <h2 className="text-2xl font-bold text-white tracking-tight">
            Portal Corporativo
          </h2>
          <p className="text-slate-400 text-sm mt-2">
            Acesso restrito a colaboradores autorizados.
          </p>
        </div>

        {/* Formulário */}
        <form onSubmit={handleLogin} className="space-y-6">
          {/* E-mail */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5 ml-1">
              E-mail Corporativo
            </label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 group-focus-within:text-white transition-colors">
                <EmailOutlined fontSize="small" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ex: admin@empresa.com"
                className="pl-10 w-full px-4 py-3 bg-slate-950/60 border border-slate-700 rounded-lg outline-none text-white placeholder-slate-600 transition-all duration-200 focus:border-[#255CA1] focus:ring-1 focus:ring-[#255CA1]"
              />
            </div>
          </div>

          {/* Senha */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5 ml-1">
              Senha
            </label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 group-focus-within:text-white transition-colors">
                <LockOutlined fontSize="small" />
              </div>
              <input
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="pl-10 pr-10 w-full px-4 py-3 bg-slate-950/60 border border-slate-700 rounded-lg outline-none text-white placeholder-slate-600 transition-all duration-200 focus:border-[#255CA1] focus:ring-1 focus:ring-[#255CA1]"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-white transition-colors outline-none"
              >
                {showPassword ? (
                  <VisibilityOff fontSize="small" />
                ) : (
                  <Visibility fontSize="small" />
                )}
              </button>
            </div>
          </div>

          {/* Mensagem de Erro */}
          {error && (
            <div className="p-3 bg-red-950/30 border border-red-900/50 text-red-400 text-sm rounded-lg text-center animate-pulse">
              {error}
            </div>
          )}

          {/* Botão Principal */}
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 text-white font-bold py-3.5 px-4 rounded-lg transform transition-all duration-200 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed mt-8"
            style={{
              backgroundColor: brandColor,
              boxShadow: `0 4px 14px 0 rgba(49, 88, 160, 0.4)`,
            }}
            onMouseOver={(e) =>
              (e.currentTarget.style.backgroundColor = "#255CA1")
            }
            onMouseOut={(e) =>
              (e.currentTarget.style.backgroundColor = brandColor)
            }
          >
            {loading ? (
              <svg
                className="animate-spin h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            ) : (
              <>
                <span>Acessar Painel</span>
                <LoginOutlined fontSize="small" />
              </>
            )}
          </button>

          {/* Rodapé / Dica */}
          <div className="text-center mt-6">
            <p className="text-xs text-slate-500">
              Problemas com acesso?{" "}
              <span className="text-#004e82-400 cursor-pointer hover:underline">
                Contate o suporte
              </span>
              .
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
