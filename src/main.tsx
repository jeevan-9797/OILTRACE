import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';

declare global {
  interface Window {
    OILTRACE_API_BASE_URL?: string;
  }
}

window.OILTRACE_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'https://oil-trace.onrender.com';

const rootEl = document.getElementById('root');
if (rootEl) {
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
