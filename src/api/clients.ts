import axios from "axios";

console.log("Variables de entorno:", {
  tenants: import.meta.env.VITE_TENANTS_URL,
  plugins: import.meta.env.VITE_PLUGINS_URL
});

export const billingApi = axios.create({
  baseURL: import.meta.env.VITE_BILLING_URL,
  timeout: 15000
});

export const iamApi = axios.create({
  baseURL: import.meta.env.VITE_IAM_SERVICE_URL,
  timeout: 15000
});

export const transactionsApi = axios.create({
  baseURL: import.meta.env.VITE_TRANSACTIONS_URL,
  timeout: 15000
});

export const tenantsApi = axios.create({
  baseURL: import.meta.env.VITE_TENANTS_URL,
  timeout: 15000
});

export const pluginsApi = axios.create({
  baseURL: import.meta.env.VITE_PLUGINS_URL,
  timeout: 15000
});

console.log("Axios tenants:", tenantsApi.defaults.baseURL);