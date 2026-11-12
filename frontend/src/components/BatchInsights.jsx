import { useState } from 'react';
import { Download } from 'lucide-react';
import { api, download } from '../api/client';
import { ActionButton, Modal } from './ui';
export default function BatchInsights(){
  const [report,setReport]=useState(null);
  return <><ActionButton variant="secondary" action={()=>api.post('/reports/batch/',{})} onDone={({data})=>setReport(data)}>Analyze learning gaps</ActionButton>{report&&<Modal wide title="Classroom learning insights" onClose={()=>setReport(null)}><p className="muted">Gemini interpretation of verified classroom results. Review these recommendations before acting on them.</p><div className="narrative"><h2>Overall learning picture</h2><p>{report.narrative.overview}</p>{[['strengths','Classroom strengths'],['learning_gaps','Learning gaps'],['teaching_recommendations','Teaching recommendations']].map(([key,title])=><div key={key}><h2>{title}</h2><ul>{report.narrative[key].map((x,i)=><li key={i}>{x}</li>)}</ul></div>)}</div><div className="form-actions"><ActionButton variant="secondary" action={()=>download(`/reports/batch/${report.id}/download/`,`skillforge-batch-${report.id}.pdf`)}><Download size={16}/>Download PDF</ActionButton></div></Modal>}</>;
}
