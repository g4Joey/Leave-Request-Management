import React, { createContext, useCallback, useContext, useMemo, useRef, useState, useEffect } from 'react';

interface ToastOptions {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

interface Toast extends ToastOptions {
  id: number;
}

interface ToastContextType {
  showToast: (opts: ToastOptions) => void;
  removeToast: (id: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

let idCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timeoutsRef = useRef<{ [key: number]: ReturnType<typeof setTimeout> }>({});

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    if (timeoutsRef.current[id]) {
      clearTimeout(timeoutsRef.current[id]);
      delete timeoutsRef.current[id];
    }
  }, []);

  const showToast = useCallback((opts: ToastOptions) => {
    const id = ++idCounter;
    const toast: Toast = {
      id,
      type: opts.type || 'info',
      message: opts.message || String(opts),
      duration: typeof opts.duration === 'number' ? opts.duration : 4000,
    };
    setToasts((prev) => [...prev, toast]);
    timeoutsRef.current[id] = setTimeout(() => removeToast(id), toast.duration);
  }, [removeToast]);

  useEffect(() => {
    return () => {
      Object.values(timeoutsRef.current).forEach(clearTimeout);
      timeoutsRef.current = {};
    };
  }, []);

  const value = useMemo(() => ({ showToast, removeToast }), [showToast, removeToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Toast container with ARIA live region */}
      <div
        className="fixed inset-x-0 top-0 z-50 flex flex-col items-center space-y-2 p-4 pointer-events-none"
        role="status"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto w-full max-w-md rounded-md border p-3 shadow-md flex items-start gap-3 ${
              t.type === 'success'
                ? 'bg-green-50 border-green-300'
                : t.type === 'error'
                ? 'bg-red-50 border-red-300'
                : t.type === 'warning'
                ? 'bg-amber-50 border-amber-300'
                : 'bg-white border-gray-200'
            }`}
          >
            <span
              className={`inline-flex h-5 w-5 flex-none items-center justify-center rounded-full text-xs font-bold ${
                t.type === 'success' ? 'bg-green-600 text-white' : t.type === 'error' ? 'bg-red-600 text-white' : t.type === 'warning' ? 'bg-amber-500 text-white' : 'bg-gray-600 text-white'
              }`}
              aria-hidden="true"
            >
              {t.type === 'success' ? '✓' : t.type === 'error' ? '!' : t.type === 'warning' ? '!' : 'i'}
            </span>
            <div className="text-sm text-gray-900 flex-1">{t.message}</div>
            <button
              onClick={() => removeToast(t.id)}
              className="ml-2 text-xs underline text-gray-600 hover:text-gray-900"
            >
              Dismiss
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
