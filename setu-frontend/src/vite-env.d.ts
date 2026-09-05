/// <reference types="vite/client" />
declare module '*.css';
declare module '*.mp4' {
  const src: string
  export default src
}