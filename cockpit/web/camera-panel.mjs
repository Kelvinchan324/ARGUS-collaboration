// Read-only camera dashboard, independent of the actuator bridge.
import {isLeaderRobot,validateEndpoint} from './core.mjs?v=so101-main-2';
const panel=document.createElement('section');
panel.className='panel camera-station';panel.hidden=true;
panel.innerHTML=`<div class="panel-head"><h2>SO-101 / Aloha camera station</h2><span class="tag muted">VIEW ONLY</span></div>
<form class="camera-connect"><label>Camera dashboard address <input type="url" required aria-label="Camera dashboard address" placeholder="http://robot-host:8000" autocomplete="off"></label><button type="submit">Open cameras</button><button type="button" data-close>Close cameras</button></form>
<p class="micro">Top / Front and both gripper views use the shared camera server. Camera health is not motor health. Direct-mode arms are NOT stopped by this page's Stop button: use the physical stop. For browser enable/stop, run the ARGUS follower bridge instead. Trusted LAN only; HTTPS pages require HTTPS camera service.</p>
<p role="status" class="camera-message">No camera dashboard loaded.</p>
<iframe title="Read-only SO-101 and Aloha camera dashboard" referrerpolicy="no-referrer" sandbox="allow-scripts allow-same-origin" allow="fullscreen" hidden></iframe>`;
document.getElementById('pane-control').append(panel);
const style=document.createElement('style');style.textContent='.camera-station{margin-top:18px;padding:16px;min-width:0}.camera-connect{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.camera-connect label{flex:1;min-width:180px}.camera-connect input{width:100%}.camera-station iframe{display:block;width:100%;height:650px;border:0;background:#101820}.camera-station iframe[hidden],.camera-station[hidden]{display:none}@media(max-width:650px){.camera-station iframe{height:900px}}';document.head.append(style);
const frame=panel.querySelector('iframe'),input=panel.querySelector('input'),message=panel.querySelector('.camera-message');
const addresses=new Map();let active='';
function close(){frame.hidden=true;frame.removeAttribute('src');message.textContent='No camera dashboard loaded.';}
function sync(){
 const id=document.getElementById('mobile-robot').value;
 const visible=document.getElementById('mode').value==='connected'&&isLeaderRobot(id)&&!document.hidden;
 if(id!==active||!visible){close();input.value=addresses.get(id)||'';active=id;}
 panel.hidden=!visible;
 if(document.getElementById('pane-control').hidden)close();
}
panel.querySelector('form').onsubmit=e=>{
 e.preventDefault();sync();if(panel.hidden)return;
 try{const url=validateEndpoint(input.value,location.protocol);addresses.set(active,url);frame.src=url+'/';frame.hidden=false;message.textContent='Read-only dashboard requested. Confirm live/offline indicators inside each view; loading does not enable arms.';}
 catch(error){close();message.textContent=error.message;}
};
panel.querySelector('[data-close]').onclick=close;
document.addEventListener('cockpit-select-robot',sync);
document.addEventListener('cockpit-view-change',sync);
document.addEventListener('visibilitychange',sync);
document.getElementById('mode').addEventListener('change',sync);
window.addEventListener('pagehide',close);
// changeMode is asynchronous; refresh only visibility, never auto-connect.
setInterval(sync,500);
