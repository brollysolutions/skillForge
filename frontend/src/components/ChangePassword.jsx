import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, clearSession, errorText } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Button, Field, useToast } from './ui';

export default function ChangePassword(){
  const [current,setCurrent]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[busy,setBusy]=useState(false);
  const {setUser}=useAuth();const navigate=useNavigate();const toast=useToast();
  async function submit(event){
    event.preventDefault();
    if(password!==confirm){toast('The new passwords do not match.','error');return;}
    setBusy(true);
    try{
      await api.post('/auth/change-password/',{current_password:current,password});
      clearSession();setUser(null);navigate('/login');toast('Password updated. Sign in with your new password.');
    }catch(error){toast(errorText(error),'error');}finally{setBusy(false);}
  }
  return <form onSubmit={submit} className="panel form-panel profile-panel"><h2>Change password</h2><p className="muted">Choose your own password after your trainer gives you access. No email is needed.</p><Field label="Current password"><input required autoComplete="current-password" type="password" value={current} onChange={e=>setCurrent(e.target.value)}/></Field><Field label="New password" hint="Use at least 10 characters."><input required minLength={10} maxLength={128} autoComplete="new-password" type="password" value={password} onChange={e=>setPassword(e.target.value)}/></Field><Field label="Confirm new password"><input required minLength={10} maxLength={128} autoComplete="new-password" type="password" value={confirm} onChange={e=>setConfirm(e.target.value)}/></Field><Button type="submit" busy={busy}>Update password</Button></form>;
}
