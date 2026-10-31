import { useState } from 'react';
import { NavLink, Outlet, Link } from 'react-router-dom';
import { LayoutDashboard, Users, BookOpen, Layers, FileText, Sparkles, ClipboardList, Send, BarChart3, FileBarChart2, Trophy, Bell, Settings, LogOut, Code2, Route, UserRound, Menu, X, Sun, Moon, ChevronRight, Command } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/ui';
const trainerLinks = [['/', 'Overview', LayoutDashboard], ['/students','Students',Users], ['/courses','Courses',BookOpen], ['/topics','Topics',Layers], ['/materials','Study materials',FileText], ['/generator','AI assignment generator',Sparkles], ['/assignments','Assignments',ClipboardList], ['/submissions','Submissions',Send], ['/performance','Student performance',BarChart3], ['/reports','AI reports',FileBarChart2], ['/leaderboard','Leaderboard',Trophy]];
const studentLinks = [['/','Overview',LayoutDashboard], ['/assignments','My assignments',ClipboardList], ['/coding','Coding practice',Code2], ['/submissions','My submissions',Send], ['/performance','My performance',BarChart3], ['/reports','AI reports',FileBarChart2], ['/learning-path','Learning path',Route], ['/leaderboard','Leaderboard',Trophy]];
export default function AppLayout() {
  const { user, logout } = useAuth(); const toast = useToast();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem('sf-theme') === 'dark');
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  const toggleTheme = () => { setDark(!dark); localStorage.setItem('sf-theme', dark ? 'light' : 'dark'); };
  const links = user.role === 'trainer' ? trainerLinks : studentLinks;
  return <div className="app-shell">
    {open && <div className="sidebar-overlay" onClick={() => setOpen(false)}/>}
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <Link to="/" className="brand"><span className="brand-mark"><Code2 size={23}/></span><span>SkillForge<span className="brand-ai">AI</span></span></Link>
      <div className="workspace-label"><span className="workspace-icon">S</span><div><strong>Learning workspace</strong><small>{user.role === 'trainer' ? 'Trainer console' : 'Student portal'}</small></div><ChevronRight size={14}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{links.map(([to,label,Icon]) => <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}><Icon size={18}/><span>{label}</span>{to === '/generator' && <span className="nav-new">AI</span>}</NavLink>)}</nav>
      <div className="sidebar-bottom"><NavLink to="/notifications" onClick={() => setOpen(false)}><Bell size={18}/>Notifications</NavLink>
        <NavLink to={user.role === 'trainer' ? '/settings' : '/profile'} onClick={() => setOpen(false)}>{user.role === 'trainer' ? <Settings size={18}/> : <UserRound size={18}/>} {user.role === 'trainer' ? 'Settings' : 'Profile'}</NavLink>
        <div className="user-card"><span className="avatar">{user.name?.[0]?.toUpperCase() || 'S'}</span><div><strong>{user.name}</strong><small>{user.role === 'trainer' ? 'Administrator' : 'Student'}</small></div><button title="Sign out" aria-label="Sign out" onClick={() => logout().catch(() => toast('Signed out locally. The server could not be reached.', 'error'))}><LogOut size={17}/></button></div>
      </div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setOpen(true)}><Menu size={21}/></button><Command size={17}/><span>Workspace</span><ChevronRight size={14}/><strong>{user.role === 'trainer' ? 'Trainer' : 'Student'}</strong></div><div className="topbar-actions"><span className="environment-dot"/> <span className="workspace-status">Your learning, connected</span><button onClick={toggleTheme} aria-label="Toggle color theme">{dark ? <Sun size={19}/> : <Moon size={19}/>}</button><Link to="/notifications" aria-label="Notifications"><Bell size={19}/></Link><Link to="/profile" className="avatar small" aria-label="Your profile">{user.name?.[0]?.toUpperCase()}</Link></div></header><main className="main-content"><Outlet/></main><footer className="app-footer"><span>SkillForge AI</span><span>Build skills. Measure growth.</span></footer></div>
  </div>;
}
