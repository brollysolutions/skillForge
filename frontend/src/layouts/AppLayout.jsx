import { useState, useEffect, useRef } from 'react';
import { NavLink, Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, BookOpen, Layers, FileText, Sparkles, ClipboardList, Send, BarChart3, FileBarChart2, Trophy, Bell, Settings, LogOut, Code2, Route, UserRound, Menu, X, Sun, Moon, ChevronRight, Command } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/ui';
const trainerLinks = [['/', 'Overview', LayoutDashboard], ['/batches','My batches',Layers], ['/students','Students',Users], ['/courses','Courses',BookOpen], ['/topics','Topics',Layers], ['/materials','Study materials',FileText], ['/generator','AI assignment generator',Sparkles], ['/assignments','Assignments',ClipboardList], ['/submissions','Submissions',Send], ['/performance','Student performance',BarChart3], ['/reports','AI reports',FileBarChart2], ['/leaderboard','Leaderboard',Trophy]];
const managerLinks = [['/','Overview',LayoutDashboard],['/team','Team access',Users],['/students','Students',Users],['/courses','Courses',BookOpen],['/batches','Batches',Layers],['/performance','Student performance',BarChart3],['/submissions','Results',FileBarChart2]];
const studentLinks = [['/','Overview',LayoutDashboard], ['/assignments','My assignments',ClipboardList], ['/coding','Coding practice',Code2], ['/submissions','My submissions',Send], ['/performance','My performance',BarChart3], ['/reports','AI reports',FileBarChart2], ['/learning-path','Learning path',Route], ['/leaderboard','Leaderboard',Trophy]];
export default function AppLayout() {
  const { user, logout } = useAuth(); const toast = useToast();
  const [open, setOpen] = useState(false);
  const [mobile,setMobile]=useState(()=>window.matchMedia?.('(max-width: 720px)')?.matches||false);
  useEffect(()=>{const media=window.matchMedia?.('(max-width: 720px)');if(!media)return;const update=()=>setMobile(media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
  const location=useLocation(); const menuButton=useRef(null); const navigation=useRef(null);
  useEffect(()=>{setOpen(false);},[location.pathname]);
  useEffect(()=>{if(!open)return;navigation.current?.querySelector('a')?.focus();const close=e=>{if(e.key==='Escape'){setOpen(false);menuButton.current?.focus();}};document.addEventListener('keydown',close);return()=>document.removeEventListener('keydown',close);},[open]);
  const [dark, setDark] = useState(() => localStorage.getItem('sf-theme') === 'dark');
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  const toggleTheme = () => { setDark(!dark); localStorage.setItem('sf-theme', dark ? 'light' : 'dark'); };
  const links = ['admin','sales'].includes(user.role) ? managerLinks : user.role === 'trainer' ? trainerLinks : studentLinks;
  const currentPage=links.find(([path])=>path==='/'?location.pathname==='/':location.pathname===path||location.pathname.startsWith(path+'/'))?.[1] || ({'/profile':'My profile','/notifications':'Notifications','/settings':'Settings'}[location.pathname]) || 'Workspace';
  return <div className="app-shell"><a href="#main-content" className="skip-link">Skip to content</a>
    {open && <div className="sidebar-overlay" onClick={() => setOpen(false)}/>}
    <aside id="workspace-navigation" inert={mobile&&!open?true:undefined} ref={navigation} className={`sidebar ${open ? 'open' : ''}`}>
      <Link to="/" className="brand"><span className="brand-mark"><Code2 size={23}/></span><span>SkillForge<span className="brand-ai">AI</span></span></Link>
      <div className="workspace-label"><span className="workspace-icon">S</span><div><strong>Learning workspace</strong><small>{`${user.role.charAt(0).toUpperCase()+user.role.slice(1)} workspace`}</small></div><ChevronRight size={14}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{links.map(([to,label,Icon]) => <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}><Icon size={18}/><span>{label}</span>{to === '/generator' && <span className="nav-new">AI</span>}</NavLink>)}</nav>
      <div className="sidebar-bottom"><NavLink to="/notifications" onClick={() => setOpen(false)}><Bell size={18}/>Notifications</NavLink>
        <NavLink to={user.role === 'trainer' ? '/settings' : '/profile'} onClick={() => setOpen(false)}>{user.role === 'trainer' ? <Settings size={18}/> : <UserRound size={18}/>} {user.role === 'trainer' ? 'Settings' : 'Profile'}</NavLink>
        <div className="user-card"><span className="avatar">{user.name?.[0]?.toUpperCase() || 'S'}</span><div><strong>{user.name}</strong><small>{user.role.charAt(0).toUpperCase()+user.role.slice(1)}</small></div><button title="Sign out" aria-label="Sign out" onClick={() => logout().catch(() => toast('Signed out locally. The server could not be reached.', 'error'))}><LogOut size={17}/></button></div>
      </div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button ref={menuButton} type="button" className="mobile-menu" aria-label={open?"Close navigation":"Open navigation"} aria-expanded={open} aria-controls="workspace-navigation" onClick={() => setOpen(!open)}><Menu size={21}/></button><Command size={17}/><span>Workspace</span><ChevronRight size={14}/><strong aria-current="page">{currentPage}</strong></div><div className="topbar-actions"><span className="environment-dot"/> <span className="workspace-status">Your learning, connected</span><button onClick={toggleTheme} aria-label="Toggle color theme" aria-pressed={dark} title={dark?"Switch to light theme":"Switch to dark theme"}>{dark ? <Sun size={19}/> : <Moon size={19}/>}</button><Link to="/notifications" aria-label="Notifications"><Bell size={19}/></Link><Link to="/profile" className="avatar small" aria-label="Your profile">{user.name?.[0]?.toUpperCase()}</Link></div></header><main id="main-content" tabIndex={-1} className="main-content"><Outlet/></main><footer className="app-footer"><span>SkillForge AI</span><span>Build skills. Measure growth.</span></footer></div>
  </div>;
}
