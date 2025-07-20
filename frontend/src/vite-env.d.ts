/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LIVEKIT_URL: string
  readonly VITE_LIVEKIT_API_KEY: string
  readonly VITE_LIVEKIT_SECRET_KEY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}