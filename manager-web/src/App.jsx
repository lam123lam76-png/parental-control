'use client';
import React, { Component } from 'react';
import FastAPIDashboard from './components/FastAPIDashboard';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Uncaught Runtime Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-black text-zinc-100 flex items-center justify-center p-6 font-mono">
          <div className="bg-zinc-900 border border-zinc-900 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-2 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <h2 className="text-sm font-bold uppercase tracking-wider">Lỗi Hiển Thị (Runtime Error)</h2>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed font-sans">
              {this.state.error?.message || "Đã xảy ra lỗi không xác định."}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 rounded text-xs font-bold text-white font-sans"
            >
              Tải Lại Trang
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <FastAPIDashboard />
    </ErrorBoundary>
  );
}