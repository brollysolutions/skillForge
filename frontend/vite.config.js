import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const projectRoot=path.dirname(fileURLToPath(import.meta.url));
function monacoAssets(){
  const source=path.join(projectRoot,'node_modules/monaco-editor/min/vs');
  let basePath='/', outputDir='dist';
  return {
    name:'local-monaco-assets',
    configResolved(config){basePath=config.base;outputDir=config.build.outDir;},
    configureServer(server){
      server.middlewares.use(`${basePath}monaco/vs`,(req,res,next)=>{
        const file=path.resolve(source,'.'+decodeURIComponent((req.url||'/').split('?')[0]));
        if(!file.startsWith(source+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return next();
        const ext=path.extname(file);
        res.setHeader('Content-Type',ext==='.js'?'application/javascript':ext==='.css'?'text/css':ext==='.ttf'?'font/ttf':'application/octet-stream');
        fs.createReadStream(file).pipe(res);
      });
    },
    closeBundle(){
      if(fs.existsSync(source))fs.cpSync(source,path.resolve(projectRoot,outputDir,'monaco/vs'),{recursive:true});
      else console.warn('Monaco is not installed locally; the functional plain-text editor fallback will be used. Run npm install to enable Monaco.');
    },
  };
}

export default defineConfig(({mode})=>{
  const env=loadEnv(mode,projectRoot,'VITE_');
  const value=process.env.VITE_BASE_PATH||env.VITE_BASE_PATH||'/';
  if(!/^\/(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]*\/?$/.test(value))throw new Error('VITE_BASE_PATH must be an absolute URL path such as /skillforge/.');
  const base=value.replace(/\/+$/,'')+'/';
  const apiPrefix=`${base}api`;
  const proxy={ [apiPrefix]: {target:process.env.SKILLFORGE_PROXY_TARGET||'http://127.0.0.1:8000',
    rewrite:url=>base==='/'?url:url.slice(base.length-1)} };
  return {
  base,
  plugins: [react(), tailwindcss(), monacoAssets()],
  server: { port: 5173, strictPort:true, proxy },
  preview: { strictPort:true, proxy },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.js', exclude: ['node_modules/**', 'e2e/**'] },
  build: { outDir:mode==='brolly'?'dist-brolly':'dist', rollupOptions: { output: { manualChunks(id) {
    if (id.includes('monaco-editor')) return 'editor';
    if (id.includes('recharts')) return 'charts';
  } } } },
};});
