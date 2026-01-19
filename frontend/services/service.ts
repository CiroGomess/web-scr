import axios, { AxiosError } from "axios";

// 1. Criação da instância do Axios
const api = axios.create({
  baseURL: "http://127.0.0.1:5000",
  // baseURL: "http://206.0.29.133/api",
  withCredentials: false,
});

// 2. INTERCEPTOR DE REQUISIÇÃO (Injeta o Token)
// Antes de qualquer requisição sair, esse código roda.
api.interceptors.request.use(
  (config) => {
    // Verifica se estamos no navegador (Client-side)
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      
      // Se tiver token, adiciona no cabeçalho Authorization
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
      data: response.data, // Aqui virá { token, user } no login
    };
  } catch (error) {
    const err = error as AxiosError;

    // 🔴 TRATAMENTO DE TOKEN EXPIRADO OU INVÁLIDO (401)
    if (err.response && err.response.status === 401) {
      if (typeof window !== "undefined") {
        // Limpa dados antigos
        localStorage.removeItem("token");
        localStorage.removeItem("user_email");
        
        // Redireciona para login se não estiver lá
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
    // Se não tem 'response', significa que o servidor não respondeu ou o navegador bloqueou.
    if (!err.response) {
      return {
        success: false, // Mudei para FALSE por segurança (evita falso positivo no login)
        status: 0,
        data: {
          message: "Erro de conexão com o servidor. Verifique se o backend está rodando.",
        },
      };
    }

    // Erro real vindo do backend (Ex: 400 Bad Request, 404 Not Found, 500 Server Error)
    return {
      success: false,
      status: err.response.status,
      data: err.response.data, // Ex: { message: "Usuário já cadastrado" }
    };
  }
};

export default services;