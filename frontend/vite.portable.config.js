// Build without helper processes in environments that restrict child-process spawning.
// The application remains JavaScript; TypeScript's parser only transforms JSX here.
import { defineConfig } from 'vite';
import ts from 'typescript';
import createBase from './vite.config.js';
export default defineConfig(configEnv=>{
const base=createBase(configEnv);
let environment={BASE_URL:base.base};
return {
  ...base,
  plugins: [
    ...base.plugins.flat().filter(plugin=>!plugin.name?.startsWith('vite:react-')),
    {
      name:'portable-jsx', enforce:'pre',
      configResolved(config){environment=config.env;},
      transform(source,id){
        if(!/\.[cm]?[jt]sx?(?:\?|$)/.test(id))return;
        if(!id.replaceAll('\\','/').includes('/src/test/'))source=source.replaceAll('process.env.NODE_ENV',JSON.stringify(process.env.NODE_ENV==='test'?'test':'production'))
          .replaceAll('import.meta.env.VITE_API_URL',JSON.stringify(environment.VITE_API_URL||''))
          .replaceAll('import.meta.env.BASE_URL',JSON.stringify(environment.BASE_URL||'/'))
          .replaceAll('process.env','({})')
          .replaceAll('import.meta.env','({})')
          .replaceAll('import.meta.hot','undefined');
        if(!/\.[jt]sx(?:\?|$)/.test(id)||id.includes('node_modules'))return {code:source,map:null};
        const output=ts.transpileModule(source,{fileName:id,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,sourceMap:true}});
        return {code:output.outputText,map:output.sourceMapText};
      },
    },
  ],
  esbuild:false,
  resolve:{preserveSymlinks:true},
  optimizeDeps:{noDiscovery:true,include:[]},
  build:{...base.build,minify:false,cssMinify:false},
};});
