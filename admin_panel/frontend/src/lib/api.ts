import axios from 'axios';
import { getToken } from '@/utils/auth';
import { API_URL } from '../config';

const api = axios.create({
    baseURL: API_URL,
});

// Add request interceptor to include Authorization header
api.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default api;
