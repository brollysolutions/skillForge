import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Code2, ArrowRight } from 'lucide-react';
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
  return <div className="auth-page">
    <div className="auth-story">
      <Link className="brand" to="/login"><span className="brand-mark"><Code2 size={18}/></span>SkillForge</Link>
      <div><h1>Assignments, review, and results in one place.</h1><p>Trainers set coding work for their batches. Students complete it, run their code, and see how they did.</p>
        <ol className="auth-steps"><li>Your trainer or sales team registers your personal email.</li><li>Enter that email here. There is no password.</li><li>Your assignments and results are waiting.</li></ol></div>
      <small>Trouble signing in? Ask your trainer to check the email they registered.</small>
    </div>
    <div className="auth-form-wrap"><div className="auth-form"><h2>Welcome back.</h2><p>Sign in with the personal email your trainer or sales team registered.</p>
      <form onSubmit={submit}><Field label="Email address"><input required type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={e=>setEmail(e.target.value)}/></Field>{error&&<div className="inline-error" role="alert">{error}</div>}<Button busy={busy} type="submit" className="full-width">Open my workspace<ArrowRight size={17}/></Button></form>
      <p className="auth-note">Anyone who knows a registered email can open that account, so keep yours private.</p></div></div>
  </div>;
}
