/// <reference types="vite/client" />

declare module "*.css" {
  const content: string;
  export default content;
}

interface ImportMetaEnv {
  readonly VITE_BILLING_URL: string;
  readonly VITE_IAM_SERVICE_URL: string;
  readonly VITE_TRANSACTIONS_URL: string;
  readonly VITE_TENANTS_URL: string;
  readonly VITE_PLUGINS_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}