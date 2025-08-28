import axios from 'axios'

const envBase: string | undefined = (import.meta as any).env?.VITE_API_BASE
const fallbackBase = `${window.location.protocol}//${window.location.hostname}:8000`
export const API_BASE = envBase || fallbackBase

const api = axios.create({
  baseURL: API_BASE,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

export default api


