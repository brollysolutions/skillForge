import { useState, useEffect, useRef } from 'react';
import { NavLink, Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, BookOpen, Layers, FileText, Sparkles, ClipboardList, Send, BarChart3, FileBarChart2, Trophy, Bell, Settings, LogOut, Code2, Route, UserRound, Menu, X, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/ui';
const trainerLinks = [['/', 'Overview', LayoutDashboard], ['/batches','My batches',Layers], ['/students','Students',Users], ['/courses','Courses',BookOpen], ['/topics','Topics',Layers], ['/materials','Study materials',FileText], ['/generator','Assignment generator',Sparkles], ['/assignments','Assignments',ClipboardList], ['/submissions','Submissions',Send], ['/performance','Student performance',BarChart3], ['/reports','Reports',FileBarChart2], ['/leaderboard','Leaderboard',Trophy]];
const managerLinks = [['/','Overview',LayoutDashboard],['/team','Team access',Users],['/students','Students',Users],['/courses','Courses',BookOpen],['/batches','Batches',Layers],['/assignments','Assignments',ClipboardList],['/performance','Student performance',BarChart3],['/submissions','Results',FileBarChart2]];
const studentLinks = [['/','Overview',LayoutDashboard], ['/assignments','My assignments',ClipboardList], ['/coding','Coding practice',Code2], ['/submissions','My submissions',Send], ['/performance','My performance',BarChart3], ['/reports','Reports',FileBarChart2], ['/learning-path','Learning path',Route], ['/leaderboard','Leaderboard',Trophy]];
export default function AppLayout() {
  const { user, logout } = useAuth(); const toast = useToast();
  const [open, setOpen] = useState(false);
  const [mobile,setMobile]=useState(()=>window.matchMedia?.('(max-width: 720px)')?.matches||false);
  useEffect(()=>{const media=window.matchMedia?.('(max-width: 720px)');if(!media)return;const update=()=>setMobile(media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
  const location=useLocation(); const menuButton=useRef(null); const navigation=useRef(null);
  useEffect(()=>{setOpen(false);},[location.pathname]);
  useEffect(()=>{
    if(!open||!mobile)return;
    const previousOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    navigation.current?.querySelector('button')?.focus();
    const close=e=>{
      if(e.key==='Escape'){setOpen(false);menuButton.current?.focus();}
      if(e.key==='Tab'){
        const controls=[...navigation.current.querySelectorAll('a[href],button:not([disabled])')];
        const first=controls[0],last=controls.at(-1);
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
      }
    };
    document.addEventListener('keydown',close);
    return()=>{document.body.style.overflow=previousOverflow;document.removeEventListener('keydown',close);menuButton.current?.focus();};
  },[open,mobile]);
  const [dark, setDark] = useState(() => localStorage.getItem('sf-theme') === 'dark');
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  const toggleTheme = () => { setDark(!dark); localStorage.setItem('sf-theme', dark ? 'light' : 'dark'); };
  const links = ['admin','sales'].includes(user.role) ? managerLinks : user.role === 'trainer' ? trainerLinks : studentLinks;
  const groups = user.role==='trainer'
    ? [['Workspace',['/','/batches','/students']],['Teaching',['/courses','/topics','/materials','/generator','/assignments']],['Progress',['/submissions','/performance','/reports','/leaderboard']]]
    : user.role==='student'
    ? [['Workspace',['/']],['Your learning',['/assignments','/coding','/submissions']],['Your progress',['/performance','/reports','/learning-path','/leaderboard']]]
    : [['Workspace',['/']],['People & courses',['/team','/students','/courses','/batches']],['Learning outcomes',['/assignments','/performance','/submissions']]];
  const currentPage=links.find(([path])=>path==='/'?location.pathname==='/':location.pathname===path||location.pathname.startsWith(path+'/'))?.[1] || ({'/profile':'My profile','/notifications':'Notifications','/settings':'Settings'}[location.pathname]) || 'Workspace';
  return <div className="app-shell"><a href="#main-content" className="skip-link">Skip to content</a>
    {open && <div className="sidebar-overlay" onClick={() => setOpen(false)}/>}
    <aside role={mobile&&open?"dialog":undefined} aria-modal={mobile&&open?true:undefined} aria-label="Workspace navigation" id="workspace-navigation" inert={mobile&&!open?true:undefined} ref={navigation} className={`sidebar ${open ? 'open' : ''}`}>
      <button type="button" className="drawer-close" aria-label="Close navigation" aria-expanded={open} onClick={()=>setOpen(false)}><X size={20}/></button><Link to="/" className="brand"><span className="brand-mark"><Code2 size={18}/></span><span>SkillForge</span></Link>
      <nav aria-label="Main navigation">{groups.map(([title,paths])=><div className="nav-group" key={title}><div className="nav-label">{title}</div>{links.filter(([path])=>paths.includes(path)).map(([to,label,Icon])=><NavLink key={to} to={to} end={to==='/'} onClick={()=>setOpen(false)}><Icon size={17}/><span>{label}</span></NavLink>)}</div>)}</nav>
      <div className="sidebar-bottom"><NavLink to="/notifications" onClick={() => setOpen(false)}><Bell size={17}/>Notifications</NavLink>
        <NavLink to={user.role === 'trainer' ? '/settings' : '/profile'} onClick={() => setOpen(false)}>{user.role === 'trainer' ? <Settings size={17}/> : <UserRound size={17}/>} {user.role === 'trainer' ? 'Settings' : 'Profile'}</NavLink>
        <div className="user-card"><span className="avatar">{user.name?.[0]?.toUpperCase() || 'S'}</span><div><strong>{user.name}</strong><small>{user.role.charAt(0).toUpperCase()+user.role.slice(1)}</small></div><button title="Sign out" aria-label="Sign out" onClick={() => logout().catch(() => toast('Signed out locally. The server could not be reached.', 'error'))}><LogOut size={17}/></button></div>
      </div>
    </aside>
    <div className="main-shell" inert={mobile&&open?true:undefined}><header className="topbar"><div className="breadcrumb"><button ref={menuButton} type="button" className="mobile-menu" aria-label={open?"Close navigation":"Open navigation"} aria-expanded={open} aria-controls="workspace-navigation" onClick={() => setOpen(!open)}><Menu size={20}/></button><strong aria-current="page">{currentPage}</strong></div><div className="topbar-actions"><button onClick={toggleTheme} aria-label="Toggle color theme" aria-pressed={dark} title={dark?"Switch to light theme":"Switch to dark theme"}>{dark ? <Sun size={17}/> : <Moon size={17}/>}</button><Link to="/notifications" aria-label="Notifications"><Bell size={17}/></Link><Link to="/profile" className="avatar small" aria-label="Your profile">{user.name?.[0]?.toUpperCase()}</Link></div></header><main id="main-content" tabIndex={-1} className="main-content"><Outlet/></main></div>
  </div>;
}
