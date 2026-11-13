import "@types/react";
import "@types/react-dom";

declare global {
  interface Window {
    api: any;
    API_PORT?: number;
  }
}

export {};
