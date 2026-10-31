import { useEffect, useState } from 'react';
import { allPages, errorText } from '../api/client';
import { Field, Button } from './ui';
export default function AnalyticsFilters({onApply}){
  const [resources,setResources]=useState({course:[],topic:[],assignment:[],student:[]}),[error,setError]=useState('');
  const [filters,setFilters]=useState({course:'',topic:'',assignment:'',student:'',date_from:'',date_to:''});
  useEffect(()=>{Promise.all([allPages('/courses/'),allPages('/topics/'),allPages('/assignments/'),allPages('/admin/students/')]).then(([course,topic,assignment,student])=>setResources({course,topic,assignment,student})).catch(e=>setError(errorText(e)));},[]);
  return <form className="panel filter-form" onSubmit={e=>{e.preventDefault();onApply(new URLSearchParams(Object.entries(filters).filter(([,v])=>v)).toString());}}>
    {Object.entries({course:'Course',topic:'Topic',assignment:'Assignment',student:'Student'}).map(([key,label])=><Field key={key} label={label}><select value={filters[key]} onChange={e=>setFilters({...filters,[key]:e.target.value,...(key==='course'?{topic:'',assignment:''}:{})})}><option value="">All {label.toLowerCase()}s</option>{resources[key].filter(x=>!['topic','assignment'].includes(key)||!filters.course||x.course===Number(filters.course)).map(x=><option key={x.id} value={x.id}>{x.title||x.name}</option>)}</select></Field>)}
    <Field label="From"><input type="date" value={filters.date_from} onChange={e=>setFilters({...filters,date_from:e.target.value})}/></Field><Field label="To"><input type="date" value={filters.date_to} onChange={e=>setFilters({...filters,date_to:e.target.value})}/></Field><Button type="submit">Apply filters</Button>{error&&<small className="error-text">{error}</small>}
  </form>;
}
