import axios, { AxiosError } from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: false,
  timeout: 21600000,
});

// Garante baseURL correta em https (seu código)
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      if (window.location.protocol === "https:") {
        if (config.url?.startsWith("http://")) {
          try {
            const urlObj = new URL(config.url);
            config.url = urlObj.pathname + urlObj.search;
          } catch (e) {}
        }
        config.baseURL = "/api";
      }
    }

    // ✅ INJETAR TOKEN AQUI (era comentado)
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

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

    if (!err.response) {
      return {
        success: false,
        status: 0,
        data: {
          message:
            "Erro de conexão com o servidor. Verifique se o backend está acessível.",
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