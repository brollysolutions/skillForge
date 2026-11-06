import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const frontend=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const integration=process.argv.includes('--integration');
const subpath=process.argv.includes('--subpath');
if(integration){
  process.env.SKILLFORGE_E2E='1';
  process.env.SF_E2E_CREDENTIALS=fs.readFileSync(path.join(frontend,'../.task-temp/browser-credentials.json'),'utf8');
  process.env.VITE_API_URL=process.env.SF_E2E_API_URL||(subpath?'http://127.0.0.1:5174/skillforge/api':'http://127.0.0.1:5173/api');
}
const {startVitest}=await import('vitest/node');
const {default:createConfig}=await import('../vite.portable.config.js');
const config=createConfig({command:'serve',mode:subpath?'brolly':'test'});
const context=await startVitest('test',integration?['src/test/integration.test.jsx']:[],{
  root:frontend,config:false,watch:false,pool:'threads',maxWorkers:1,mode:subpath?'brolly':'test',
},{...config,configFile:false,test:{...config.test,pool:'threads',maxWorkers:1,
  environmentOptions:{jsdom:{url:subpath?'http://127.0.0.1:5174/skillforge/':'http://127.0.0.1:5173'}}}});
if(context)await context.close();
