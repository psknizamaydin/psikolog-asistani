import {defineConfig} from 'vite';
import tailwindcss from '@tailwindcss/vite';
const domain=process.env.GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN;
const name=process.env.CODESPACE_NAME;
export default defineConfig({plugins:[tailwindcss()],server:{host:'0.0.0.0',allowedHosts:domain&&name?[`${name}-5173.${domain}`]:[],proxy:{'/api':{target:'http://127.0.0.1:8000',changeOrigin:true,rewrite:path=>path.replace(/^\/api/,'')}}}});
