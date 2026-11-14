import { useEffect, useRef, useState } from 'react';
let loaderPromise;
function loadMonaco() {
  if (window.monaco?.editor) return Promise.resolve(window.monaco);
  if (!loaderPromise) loaderPromise = new Promise((resolve,reject) => {
    const timeout=setTimeout(()=>reject(new Error('Editor could not load.')),12000);
    const script=document.createElement('script');
    script.src=`${import.meta.env.BASE_URL}monaco/vs/loader.js`;
    script.onload=()=>{
      window.require.config({paths:{vs:`${import.meta.env.BASE_URL}monaco/vs`}});
      window.require(['vs/editor/editor.main'],()=>{clearTimeout(timeout);resolve(window.monaco);},()=>{clearTimeout(timeout);reject(new Error('Editor unavailable.'));});
    };
    script.onerror=()=>{clearTimeout(timeout);reject(new Error('Editor unavailable.'));};
    document.head.appendChild(script);
  });
  return loaderPromise;
}
export default function CodeEditor({value,onChange,readOnly=false}) {
  const host=useRef(null),editor=useRef(null),onChangeRef=useRef(onChange),valueRef=useRef(value);
  const [fallback,setFallback]=useState(false),[ready,setReady]=useState(false);
  onChangeRef.current=onChange;valueRef.current=value;
  useEffect(()=>{
    let disposed=false;let listener;
    loadMonaco().then(monaco=>{
      if(disposed)return;
      editor.current=monaco.editor.create(host.current,{value:valueRef.current,language:'python',theme:document.documentElement.dataset.theme==='dark'?'vs-dark':'vs',fontSize:14,minimap:{enabled:false},padding:{top:18},scrollBeyondLastLine:false,automaticLayout:true,tabSize:4,wordWrap:'on',ariaLabel:'Python code editor',readOnly});
      listener=editor.current.onDidChangeModelContent(()=>onChangeRef.current(editor.current.getValue()));
      setReady(true);
    }).catch(()=>{if(!disposed)setFallback(true);});
    return()=>{disposed=true;listener?.dispose();const model=editor.current?.getModel();editor.current?.dispose();model?.dispose();editor.current=null;};
  },[]);
  useEffect(()=>{if(editor.current&&editor.current.getValue()!==value)editor.current.setValue(value);},[value]);
  useEffect(()=>{editor.current?.updateOptions({readOnly});},[readOnly,ready]);
  if(fallback)return <div className="editor-fallback"><p>Advanced editor unavailable. You can still write, run, and submit Python below.</p><textarea readOnly={readOnly} aria-label="Python code editor" spellCheck={false} className="code-input" value={value} onChange={e=>onChange(e.target.value)} style={{height:380,borderRadius:0,border:0}}/></div>;
  return <div style={{position:'relative'}}>{!ready&&<p className="editor-loading">Loading Python editor…</p>}<div ref={host} style={{height:420}}/></div>;
}
