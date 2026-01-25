import axios, { AxiosError } from "axios";

// =====================================================================
// 🌍 AMBIENTE: LOCAL (ATIVO)
// =====================================================================
// Use esta configuração para rodar localmente sem o prefixo /api
const api = axios.create({
  baseURL: "http://127.0.0.1:5000",
  withCredentials: false, // Geralmente false para CORS simples local, ajuste se necessário
  timeout: 21600000, // 6 horas
});


// =====================================================================
// 🚀 AMBIENTE: PRODUÇÃO (COMENTADO)
// =====================================================================
/*
// 1. Criação da instância do Axios para Produção
// O Nginx faz o proxy reverso, então usamos URL relativa e prefixo /api
const api = axios.create({
  baseURL: "/api",
  withCredentials: false,
  timeout: 21600000,
});

// Interceptor específico de PRODUÇÃO para garantir protocolo correto via Proxy
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      if (window.location.protocol === "https:") {
        if (config.url?.startsWith("http://")) {
          try {
            const urlObj = new URL(config.url);
            config.url = urlObj.pathname + urlObj.search;
          } catch (e) {
             // URL inválida, mantém original
          }
        }
        config.baseURL = "/api";
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
*/

// =====================================================================
// 🔐 CONFIGURAÇÕES GERAIS (COMUNS AOS DOIS AMBIENTES)
// =====================================================================

// 2. INTERCEPTOR DE REQUISIÇÃO (Injeta o Token)
// Funciona tanto local quanto produção
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 3. FUNÇÃO WRAPPER (Padroniza a resposta)
const services = async (endpoint: string, options: any = {}) => {
  try {
    const response = await api.request({
      url: endpoint,
      ...options,
    });

    return {
      success: true,
      status: response.status,
      data: response.data, 
    };
  } catch (error) {
    const err = error as AxiosError;

    // 🔴 TRATAMENTO DE TOKEN EXPIRADO OU INVÁLIDO (401)
    if (err.response && err.response.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        localStorage.removeItem("user_email");
        
        if (!window.location.pathname.includes("/login")) {
             window.location.href = "/login";
        }
      }
      return {
        success: false,
        status: 401,
        data: { message: "Sessão expirada. Faça login novamente." },
      };
    }

    // 🚨 NETWORK / CORS error
    if (!err.response) {
      return {
        success: false,
        status: 0,
        data: {
          message: "Erro de conexão com o servidor. Verifique se o backend está rodando em http://127.0.0.1:5000",
        },
      };
    }

    return {
      success: false,
      status: err.response.status,
      data: err.response.data,
    };
  }
};

export default services;