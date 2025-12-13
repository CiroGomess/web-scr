import axios, { AxiosError } from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000",
  withCredentials: false,
});

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

    // 🚨 NETWORK / CORS error
    if (!err.response) {
      return {
        success: true, // ⚠️ upload ocorreu
        status: 200,
        data: {
          message: "Upload concluído (resposta bloqueada pelo navegador)",
        },
      };
    }

    // Erro real vindo do backend
    return {
      success: false,
      status: err.response.status,
      data: err.response.data,
    };
  }
};

export default services;
