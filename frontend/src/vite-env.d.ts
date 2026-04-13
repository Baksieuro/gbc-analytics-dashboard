/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  /** Опционально: ISO-код валюты для подписей на графиках (перекрывает авто-детект). */
  readonly VITE_DISPLAY_CURRENCY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
