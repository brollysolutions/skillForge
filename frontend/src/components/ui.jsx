import { createContext, useContext, useState, useRef, useEffect } from 'react';
import { AlertCircle, CheckCircle2, X, LoaderCircle, Inbox, ChevronLeft, ChevronRight } from 'lucide-react';
import { errorText } from '../api/client';
const ToastContext = createContext(null);
export const useToast = () => useContext(ToastContext);
export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timer = useRef();
  const show = (message, type = 'success') => { clearTimeout(timer.current); setToast({ message, type }); timer.current = setTimeout(() => setToast(null), 6000); };
  useEffect(() => () => clearTimeout(timer.current), []);
  return <ToastContext.Provider value={show}>{children}{toast && <div role="status" className={`toast ${toast.type}`}>
    {toast.type === 'error' ? <AlertCircle size={20}/> : <CheckCircle2 size={20}/>}<span>{toast.message}</span><button aria-label="Dismiss notification" onClick={() => setToast(null)}><X size={17}/></button>
  </div>}</ToastContext.Provider>;
}
export function Button({ children, busy, variant = 'primary', className = '', ...props }) {
  return <button {...props} disabled={busy || props.disabled} className={`btn btn-${variant} ${className}`}>{busy && <LoaderCircle size={16} className="spin"/>}{children}</button>;
}
export function ActionButton({ action, onDone, children, success, confirm, ...props }) {
  const [busy, setBusy] = useState(false); const toast = useToast(); const [confirming, setConfirming] = useState(false);
  async function run() { if (busy) return; setConfirming(false); setBusy(true); try { const result = await action(); if (success) toast(success); onDone?.(result); } catch (e) { toast(errorText(e), 'error'); } finally { setBusy(false); } }
  return <><Button {...props} busy={busy} onClick={() => confirm ? setConfirming(true) : run()}>{children}</Button>
    {confirming && <Modal title="Please confirm" onClose={() => setConfirming(false)}><p>{confirm}</p><div className="form-actions"><Button variant="secondary" onClick={() => setConfirming(false)}>Cancel</Button><Button onClick={run}>Confirm</Button></div></Modal>}</>;
}
export function Field({ label, error, children, hint }) { return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}{error && <small className="error-text">{error.message || error}</small>}</label>; }
export function Badge({ children, tone }) { return <span className={`badge ${tone || String(children).toLowerCase().replaceAll(' ', '_')}`}>{String(children).replaceAll('_', ' ')}</span>; }
export function Empty({ title = 'Nothing here yet', description = 'Your records will appear here as you get started.', action }) { return <div className="empty"><span className="empty-icon"><Inbox size={28}/></span><h3>{title}</h3><p>{description}</p>{action}</div>; }
export function Loading() { return <div className="skeleton-stack" aria-label="Loading"><div className="skeleton"/><div className="skeleton"/><div className="skeleton"/></div>; }
export function ErrorState({ message, retry }) { return <div className="error-state" role="alert"><AlertCircle size={24}/><p>{message}</p>{retry && <Button variant="secondary" onClick={retry}>Try again</Button>}</div>; }
export function PageHeader({ eyebrow = 'YOUR WORKSPACE', title, description, children }) { return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div><div className="header-actions">{children}</div></div>; }
export function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef(null);
  useEffect(() => { ref.current.showModal(); }, []);
  return <dialog ref={ref} className={`modal ${wide ? 'wide' : ''}`} onCancel={e => { e.preventDefault(); onClose(); }}><div className="modal-heading"><h2>{title}</h2><button onClick={onClose} aria-label="Close dialog"><X size={22}/></button></div>{children}</dialog>;
}
export function Pagination({ data, page, setPage }) {
  if (!data || data.count <= 20) return null;
  return <div className="pagination"><span>{data.count} records · Page {page}</span><Button variant="secondary" disabled={!data.previous} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16}/> Previous</Button><Button variant="secondary" disabled={!data.next} onClick={() => setPage(p => p + 1)}>Next <ChevronRight size={16}/></Button></div>;
}
export const formatDate = value => value ? new Date(value).toLocaleString(undefined, { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }) : 'No deadline';
