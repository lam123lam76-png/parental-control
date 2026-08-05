'use client';
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// DIAGNOSTIC MOUNT & GLOBAL ERROR HANDLER (CHỐNG MÀN HÌNH ĐEN HOÀN TOÀN)
function renderDiagnosticError(errorMsg, stackInfo = '') {
  try {
    const errorHtml = `
      <div style="min-height: 100vh; background-color: #000000; color: #f4f4f5; font-family: monospace; display: flex; align-items: center; justify-content: center; padding: 24px; box-sizing: border-box;">
        <div style="background-color: #111111; border: 1px solid #27272a; border-radius: 12px; padding: 24px; max-width: 500px; width: 100%; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <span style="width: 8px; height: 8px; border-radius: 9999px; background-color: #f43f5e; display: inline-block;"></span>
            <h2 style="font-size: 14px; font-weight: 700; margin: 0; color: #f43f5e; text-transform: uppercase; letter-spacing: 0.05em;">Chẩn Đoán Lỗi Runtime (Diagnostic Error)</h2>
          </div>
          <p style="font-size: 12px; color: #a1a1aa; line-height: 1.5; font-family: sans-serif; margin-bottom: 16px;">
            Trình duyệt gặp sự cố khi khởi chạy ứng dụng. Dưới đây là thông tin chi tiết lỗi:
          </p>
          <div style="background-color: #000000; border: 1px solid #27272a; border-radius: 6px; padding: 12px; font-size: 11px; color: #fda4af; overflow-x: auto; max-height: 150px; margin-bottom: 16px; white-space: pre-wrap; word-break: break-all;">
            ${errorMsg || 'Uncaught Script Execution Exception'}\n${stackInfo}
          </div>
          <button
            onclick="if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(r=>{for(let reg of r)reg.unregister();});} localStorage.clear(); sessionStorage.clear(); window.location.reload();"
            style="width: 100%; background-color: #ffffff; color: #000000; font-weight: 600; padding: 10px; border-radius: 6px; font-size: 12px; border: none; cursor: pointer; transition: background 0.2s;"
          >
            Xóa Cache & Tải Lại Trang
          </button>
        </div>
      </div>
    `;
    document.body.innerHTML = errorHtml;
  } catch (e) {
    console.error('Failed to render diagnostic error:', e);
  }
}

// Bắt lỗi toàn cục window.onerror & unhandledrejection
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    console.error('Global Error Captured:', event.error);
    renderDiagnosticError(event.message, event.error?.stack || '');
  });

  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled Rejection Captured:', event.reason);
    renderDiagnosticError(
      typeof event.reason === 'object' ? event.reason?.message || 'Unhandled Promise Rejection' : String(event.reason),
      event.reason?.stack || ''
    );
  });

  // Tự động Unregister Service Worker cũ để bust stale PWA cache
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      for (let registration of registrations) {
        registration.unregister();
      }
    }).catch((err) => {
      console.warn('Service worker unregister error:', err);
    });
  }
}

// KIỂM TRA PHẦN TỬ #ROOT AN TOÀN
let rootElement = document.getElementById('root');
if (!rootElement) {
  rootElement = document.createElement('div');
  rootElement.id = 'root';
  document.body.appendChild(rootElement);
}

try {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
} catch (err) {
  console.error('React Root Mount Error:', err);
  renderDiagnosticError(err?.message || 'React Root Mount Exception', err?.stack || '');
}
