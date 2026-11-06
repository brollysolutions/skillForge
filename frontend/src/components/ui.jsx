import { createContext, useContext, useState, useRef, useEffect, useId, Children, cloneElement, isValidElement } from 'react';
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
export function Button({ children, busy, type = 'button', variant = 'primary', className = '', ...props }) {
  return <button {...props} type={type} aria-busy={busy || undefined} disabled={busy || props.disabled} className={`btn btn-${variant} ${className}`}>{busy && <LoaderCircle size={16} className="spin" aria-hidden="true"/>}{children}</button>;
}
export function ActionButton({ action, onDone, children, success, confirm, ...props }) {
  const [busy, setBusy] = useState(false); const toast = useToast(); const [confirming, setConfirming] = useState(false);
  async function run() { if (busy) return; setConfirming(false); setBusy(true); try { const result = await action(); if (success) toast(success); onDone?.(result); } catch (e) { toast(errorText(e), 'error'); } finally { setBusy(false); } }
  return <><Button {...props} busy={busy} onClick={() => confirm ? setConfirming(true) : run()}>{children}</Button>
    {confirming && <Modal title="Please confirm" onClose={() => setConfirming(false)}><p>{confirm}</p><div className="form-actions"><Button variant="secondary" onClick={() => setConfirming(false)}>Cancel</Button><Button onClick={run}>Confirm</Button></div></Modal>}</>;
}
export function Field({ label, error, children, hint }) {
  const generatedId = useId();
  const items = Children.toArray(children);
  const control = items.find(child => isValidElement(child) && ['input', 'select', 'textarea'].includes(child.type));
  const id = control?.props.id || generatedId;
  const describedBy = [control?.props['aria-describedby'], hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined;
  return <div className="field"><label htmlFor={id} className="field-label">{label}</label>{items.map(child => child === control ? cloneElement(child, {id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined}) : child)}{hint && <small id={`${id}-hint`}>{hint}</small>}{error && <small id={`${id}-error`} className="error-text">{error.message || error}</small>}</div>;
}
const badgeGroups = {
  positive: ['active','published','evaluated','completed','approved','accepted','on_track','results_released','configured','easy','passed'],
  caution: ['pending','pending_review','needs_review','needs_support','submitted','medium','awaiting_evidence','overdue'],
  negative: ['inactive','failed','error','wrong_answer','hard','not_configured','mismatched'],
  info: ['in_progress','grading','trainer','student','sales','admin','coding','debugging','mixed'],
};
const badgeLabels = {mcq:'Multiple choice',multiple_select:'Multiple select',fill_blank:'Fill in the blank',genai_practical:'AI practical',not_started:'Not started',in_progress:'In progress',pending_review:'Needs review',output_prediction:'Output prediction',short_answer:'Short answer'};
export function Badge({ children, tone }) {
  const raw = children == null || children === '' ? 'Not set' : String(children);
  const key = raw.toLowerCase().replaceAll(' ', '_');
  const toneKey = String(tone || key).toLowerCase().replaceAll(' ', '_');
  const group = Object.entries(badgeGroups).find(([name, values]) => name === toneKey || values.includes(toneKey))?.[0] || 'neutral';
  const label = badgeLabels[key] || raw.replaceAll('_',' ').replace(/^\w/, c => c.toUpperCase());
  return <span className={`badge ${key}`} data-tone={group}><span className="badge-dot" aria-hidden="true"/>{label}</span>;
}
export function Empty({ title = 'Nothing here yet', description = 'Your records will appear here as you get started.', action }) { return <div className="empty"><span className="empty-icon"><Inbox size={28}/></span><h3>{title}</h3><p>{description}</p>{action}</div>; }
export function Loading() { return <div className="skeleton-stack" role="status" aria-label="Loading" aria-busy="true"><div className="skeleton"/><div className="skeleton"/><div className="skeleton"/></div>; }
export function ErrorState({ message, retry }) { return <div className="error-state" role="alert"><AlertCircle size={24}/><p>{message}</p>{retry && <Button variant="secondary" onClick={retry}>Try again</Button>}</div>; }
export function PageHeader({ eyebrow = 'YOUR WORKSPACE', title, description, children }) { return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div><div className="header-actions">{children}</div></div>; }
export function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => { const previous = document.activeElement; ref.current.showModal(); return () => { if (previous?.isConnected) previous.focus(); }; }, []);
  return <dialog ref={ref} aria-labelledby={titleId} className={`modal ${wide ? 'wide' : ''}`} onCancel={e => { e.preventDefault(); onClose(); }}><div className="modal-heading"><h2 id={titleId}>{title}</h2><button type="button" onClick={onClose} aria-label="Close dialog"><X size={22}/></button></div>{children}</dialog>;
}
export function Pagination({ data, page, setPage }) {
  if (!data || data.count <= 20) return null;
  return <div className="pagination"><span>{data.count} records · Page {page}</span><Button variant="secondary" disabled={!data.previous} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16}/> Previous</Button><Button variant="secondary" disabled={!data.next} onClick={() => setPage(p => p + 1)}>Next <ChevronRight size={16}/></Button></div>;
}
export const formatDate = value => value ? new Date(value).toLocaleString(undefined, { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }) : 'No deadline';
