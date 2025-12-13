// src/services/services.tsx
import axios, { AxiosError } from 'axios';

const api = axios.create({
    baseURL: 'http://127.0.0.1:5000/',
    headers: { 'Content-Type': 'application/json' },
});

const services = async (endpoint: string, options = {}) => {
    try {
        const response = await api.request({ url: endpoint, ...options });
        return { success: true, status: response.status, data: response.data };
    } catch (error: unknown) {
        const err = error as AxiosError;
        return {
            success: false,
            status: err.response?.status || 500,
            data: err.response?.data || { message: 'Erro interno' },
        };
    }
}


export default services;