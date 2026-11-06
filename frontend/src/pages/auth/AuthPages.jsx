import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Code2, ArrowRight, ShieldCheck, Sparkles, BarChart3 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { errorText } from '../../api/client';
import { Button, Field } from '../../components/ui';

export default function AuthPage() {
  const { user, login } = useAuth(); const navigate = useNavigate();
  const [email, setEmail] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace/>;
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await login({email: email.trim().toLowerCase()}); navigate('/'); }
    catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  return <div className="auth-page"><div className="auth-story"><Link className="brand" to="/login"><span className="brand-mark"><Code2 size={25}/></span>SkillForge<span className="brand-ai">AI</span></Link><div><span className="auth-kicker">ONE TASK. REAL PROGRESS.</span><h1>Practice with purpose.<br/><em>See your progress.</em></h1><p>Your batches, assignments, and results. One place to keep learning.</p><div className="auth-features"><span><Code2/> Clear tasks and expected outputs</span><span><Sparkles/> AI-assisted assignments</span><span><BarChart3/> Results you can understand</span></div></div><small>Built for students. Connected by trainers.</small></div><div className="auth-form-wrap"><div className="auth-form"><div className="auth-icon"><ShieldCheck size={26}/></div><h2>Welcome back.</h2><p>Enter the personal email address registered by your trainer or sales team.</p><form onSubmit={submit}><Field label="Email address"><input required type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={e=>setEmail(e.target.value)}/></Field>{error&&<div className="inline-error" role="alert">{error}</div>}<Button busy={busy} type="submit" className="full-width">Open my workspace<ArrowRight size={18}/></Button></form><div className="auth-note">No password. No login email. Your registered email opens your account.</div></div></div></div>;
}
