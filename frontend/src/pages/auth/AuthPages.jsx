import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Code2, ArrowRight, ShieldCheck, Sparkles, BarChart3 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api, errorText } from '../../api/client';
import { Button, Field, useToast } from '../../components/ui';

export default function AuthPage({ mode = 'login' }) {
  const { user, login } = useAuth(); const navigate = useNavigate(); const toast = useToast(); const [params] = useSearchParams();
  const resetConfirm = mode === 'reset' && params.has('token');
  const needsEmail = mode === 'login' || (mode === 'reset' && !resetConfirm);
  const needsPassword = mode === 'login' || mode === 'invite' || resetConfirm;
  const schema = z.object({ ...(needsEmail ? { email: z.email('Enter a valid email address.') } : {}), ...(needsPassword ? { password: z.string().min(mode === 'login' ? 1 : 10, 'Use at least 10 characters.') } : {}) });
  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm({ resolver:zodResolver(schema) });
  if (user && mode === 'login') return <Navigate to="/" replace/>;
  const title = mode === 'login' ? 'Welcome back.' : mode === 'invite' ? 'Your next chapter starts here.' : resetConfirm ? 'Choose a new password.' : 'Reset your password.';
  async function submit(values) {
    try {
      if (mode === 'login') { await login(values); navigate('/'); }
      else if (mode === 'invite') { await api.post('/auth/invitations/accept/', {...values, token:params.get('token')}); toast('Your account is ready. Sign in to get started.'); navigate('/login'); }
      else if (resetConfirm) { await api.post('/auth/password-reset/confirm/', {...values, uid:params.get('uid'), token:params.get('token')}); toast('Password updated.'); navigate('/login'); }
      else { const { data } = await api.post('/auth/password-reset/', values); toast(data.detail); }
    } catch (e) { setError('root', { message:errorText(e) }); }
  }
  return <div className="auth-page"><div className="auth-story"><Link className="brand" to="/login"><span className="brand-mark"><Code2 size={25}/></span>SkillForge<span className="brand-ai">AI</span></Link><div><span className="auth-kicker">THE NEXT GENERATION OF LEARNING</span><h1>Knowledge is a start.<br/><em>Mastery is the goal.</em></h1><p>A focused space to practice, prove your skills, and discover what comes next.</p><div className="auth-features"><span><Code2/> Real coding challenges</span><span><Sparkles/> Personalized learning insights</span><span><BarChart3/> Progress you can measure</span></div></div><small>Designed for curious minds. Built for meaningful progress.</small></div><div className="auth-form-wrap"><div className="auth-form"><div className="auth-icon"><ShieldCheck size={26}/></div><h2>{title}</h2><p>{mode === 'login' ? 'Use your authorized email and password to open your dashboard.' : mode === 'invite' ? 'Set a password to accept your trainer’s invitation.' : 'We’ll help you get back to your workspace.'}</p><form onSubmit={handleSubmit(submit)}>
    {needsEmail && <Field label="Email address" error={errors.email}><input type="email" autoComplete="username" placeholder="you@youracademy.com" {...register('email')}/></Field>}
    {needsPassword && <Field label="Password" error={errors.password}><input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder="Enter your password" {...register('password')}/></Field>}
    {mode === 'login' && <Link className="forgot-link" to="/reset-password">Forgot password?</Link>}
    {errors.root && <div className="inline-error" role="alert">{errors.root.message}</div>}
    <Button busy={isSubmitting} type="submit" className="full-width">{mode === 'login' ? 'Sign in to workspace' : mode === 'invite' ? 'Activate my account' : resetConfirm ? 'Update password' : 'Send reset link'}<ArrowRight size={18}/></Button>
    </form><div className="auth-note">{mode === 'login' ? <><ShieldCheck size={15}/> Ask your trainer to add your email and share your sign-in password.</> : <Link to="/login">Back to sign in</Link>}</div></div></div></div>;
}
