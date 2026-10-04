import './layout.mjs';
import {ROBOTS,STALE_MS,emptyState,demoState,fresh,finite,clamp,normalizeAR,normalizeGeneric,validateEndpoint,commandRequest,jsonRequest,CommandChannel} from './core.mjs';
const $=id=>document.getElementById(id);
let selected=ROBOTS[0].id,mode='demo',hold=null,transition=false,videoMode=false;
const records=new Map(ROBOTS.map((robot,i)=>[robot.id,{robot,demo:demoState(robot,i),state:emptyState(),config:null,channel:null,version:0,controlEpoch:0,polling:false,authorized:false,busy:false,history:[],rightJoints:[0,-12,24,0,12,0],leftJoints:[0,-12,24,0,12,0],lastError:''}]));
const logs=[];
let vrSupport='Checking browser VR support';
if(navigator.xr?.isSessionSupported){navigator.xr.isSessionSupported('immersive-vr').then(supported=>{vrSupport=supported?'VR available · no active session':'Immersive VR unavailable';}).catch(()=>{vrSupport='VR support could not be checked';});}else{vrSupport='WebXR unavailable in this browser';}
function cockpitSnapshot(){
 let gamepads=[];try{gamepads=[...(navigator.getGamepads?.()||[])].filter(p=>p?.connected);}catch{/* Device access may be restricted by the browser. */}
 const armed=[...records.values()].filter(r=>r.authorized&&state(r).enabled&&fresh(state(r)));
 return {stationFocused:document.hasFocus()&&!document.hidden,source:mode,armedRobotIds:armed.map(r=>r.robot.id),freshRobotLinks:mode==='connected'?[...records.values()].filter(r=>r.config&&fresh(r.state)).length:0,vrSession:'not connected',vrSupport,gamepadsDetected:gamepads.length,leaderArms:'not configured',footPedals:'not configured',physicalEmergencyStop:'unverified',hardwareReady:false};
}
function renderCockpit(){
 const c=cockpitSnapshot();$('station-status').textContent=c.stationFocused?'Operator page active':'Operator page unfocused';$('station-detail').textContent=c.stationFocused?'Keyboard and pointer available':'Motion locks when focus is lost';
 $('route-status').textContent=c.armedRobotIds.length?(mode==='demo'?'Demo control enabled':'Robot control enabled'):'Control locked';$('route-detail').textContent=c.armedRobotIds.length?c.armedRobotIds.map(id=>records.get(id).robot.name).join(', '):'No robot armed by this cockpit';
 $('links-status').textContent=mode==='demo'?'Demo session':`${c.freshRobotLinks} / 6 fresh links`;$('links-detail').textContent=mode==='demo'?'Local simulation · no hardware traffic':'Fresh links may include bridge simulation';
 $('vr-status').textContent='Not connected';$('vr-detail').textContent=c.vrSupport;$('input-status').textContent=c.gamepadsDetected?`${c.gamepadsDetected} gamepad(s) detected`:'Keyboard / pointer';$('input-detail').textContent=c.gamepadsDetected?'Detected only · no robot mapping':'No gamepad detected';
}
const record=()=>records.get(selected);
const state=r=>mode==='demo'?r.demo:r.state;
const fmt=(v,unit='',digits=0)=>finite(v)===null?'—':`${v.toFixed(digits)}${unit}`;
function notice(text,error=false){$('notice').textContent=text;$('notice').classList.toggle('error',error);}
function log(message,error=false){logs.unshift({time:new Date().toLocaleTimeString('en-GB'),message,error});logs.splice(100);const li=document.createElement('li');if(error)li.className='error';const t=document.createElement('time');t.textContent=logs[0].time;const span=document.createElement('span');span.textContent=message;li.append(t,span);$('events').prepend(li);while($('events').children.length>100)$('events').lastChild.remove();}
function configured(r){return mode==='demo'||!!r.config;}
function canDrive(r){const s=state(r);return !$('pane-control').hidden&&!transition&&fresh(s)&&s.capabilities.drive&&r.authorized&&s.enabled;}
function buildFleet(){for(const r of records.values()){
 const mobileOption=document.createElement('option');mobileOption.value=r.robot.id;mobileOption.textContent=r.robot.name;$('mobile-robot').append(mobileOption);
 const button=document.createElement('button');button.className='robot-option';button.dataset.robot=r.robot.id;button.innerHTML='<span class="robot-avatar"></span><span><strong></strong><small><i></i><span></span></small></span>';
 button.querySelector('.robot-avatar').textContent=r.robot.short;button.querySelector('strong').textContent=r.robot.name;button.onclick=()=>selectRobot(r.robot.id);$('fleet').append(button);
 const option=document.createElement('option');option.value=r.robot.id;option.textContent=r.robot.name;$('connection-robot').append(option);
 const card=document.createElement('form');card.className='robot-connection-card';card.dataset.connection=r.robot.id;
 card.innerHTML='<div class="connection-card-title"><h3></h3><span class="connection-status">Not configured</span></div><p class="connection-protocol"></p><label>Bridge address<input type="url" required autocomplete="off" placeholder="https://robot-bridge.example"></label><div class="connection-actions"><button type="submit">Connect</button><button type="button" data-disconnect>Disconnect</button><button type="button" data-options>Options</button></div><p class="connection-card-error" role="alert"></p>';
 card.querySelector('h3').textContent=r.robot.name;card.querySelector('.connection-protocol').textContent=r.robot.id==='robot-ar'?'Robot-AR bridge · existing integration':'ARGUS v1 · hardware adaptor required';
 card.querySelector('input').setAttribute('aria-label',`${r.robot.name} bridge address`);
 if(r.robot.id==='robot-ar'&&location.pathname.startsWith('/cockpit/'))card.querySelector('input').value=location.origin;
 card.onsubmit=async e=>{e.preventDefault();const error=card.querySelector('.connection-card-error');error.textContent='';try{await connectRobot(r,card.querySelector('input').value,r.config?.token||'');}catch(ex){error.textContent=`Could not connect: ${ex.message}`;}};
 card.querySelector('[data-disconnect]').onclick=()=>disconnectRobot(r);
 card.querySelector('[data-options]').onclick=()=>{$('connection-robot').value=r.robot.id;fillConnection();$('endpoint').value=card.querySelector('input').value;$('connection-dialog').showModal();};
 $('robot-connections-grid').append(card);
}}
async function send(r,action,payload={},interrupt=false){
 if(mode==='demo'){
  if(action==='stop'){r.demo.enabled=false;r.authorized=false;r.demo.vx=0;r.demo.wz=0;r.demo.task='Stopped';}
  if(action==='enable'){r.demo.enabled=payload.enabled;r.authorized=payload.enabled;r.demo.task=payload.enabled?'Manual control':'Standby';}
  if(action==='drive'){r.demo.vx=payload.vx;r.demo.wz=payload.wz;}
  return {ok:true};
 }
 if(!r.channel)throw Error('No adaptor connection');
 return r.channel.run(action,payload,interrupt);
}
async function halt(r,disable=false,quiet=false){
 if(hold?.id===r.robot.id){hold=null;document.querySelectorAll('.held').forEach(b=>b.classList.remove('held'));}
 if(disable){r.authorized=false;r.controlEpoch++;}
 if(!configured(r))return;
 try{const result=await send(r,disable?'stop':'drive',disable?{}:{vx:0,wz:0},true);if(!quiet&&!result.skipped)log(`${r.robot.name}: ${mode==='demo'?'simulated stop':'stop acknowledged'}.`);}
 catch(e){r.authorized=false;log(`${r.robot.name}: STOP NOT CONFIRMED — ${e.message}`,true);notice('Stop could not be confirmed. Use the robot’s physical stop if needed.',true);}
 render();
}
async function stopAll(){
 if(hold){hold=null;document.querySelectorAll('.held').forEach(b=>b.classList.remove('held'));}
 await Promise.all([...records.values()].filter(configured).map(r=>halt(r,true)));
}
async function selectRobot(id){
 if(id===selected)return;
 const previous=record();if(previous.authorized||previous.busy||hold?.id===selected)await halt(previous,true);
 selected=id;videoMode=false;$('inspection-video').pause();updateSelection();render();document.dispatchEvent(new Event('cockpit-select-robot'));
}
function updateSelection(){
 $('mobile-robot').value=selected;
 const r=record(),robot=r.robot;$('robot-name').textContent=robot.name;$('robot-code').textContent=robot.short;$('robot-kind').textContent=`${robot.kind} · ${robot.status}`;
 $('view-robot').textContent=`${robot.short} / ${String(ROBOTS.indexOf(robot)+1).padStart(2,'0')}`;
 $('robot-image').hidden=!robot.image;if(robot.image)$('robot-image').src=robot.image;
 $('robot-image').alt=`${robot.name} reference model or photograph`;$('robot-symbol').hidden=!!robot.image;$('robot-symbol').textContent=robot.short;
 $('video-view').disabled=robot.id!=='bimanual-bunker-mini';$('arm-tools').hidden=!robot.arms;$('lift-tools').hidden=!robot.lift;$('leg-tools').hidden=!robot.legs;
 $('connection-robot').value=selected;showView();
}
function showView(){
 $('inspection-video').hidden=!videoMode;$('robot-image').hidden=videoMode||!record().robot.image;$('robot-symbol').hidden=videoMode||!!record().robot.image;
 $('view-label').textContent=videoMode?'RECORDED CONCEPT':'ROBOT REFERENCE';$('preview-view').classList.toggle('active',!videoMode);$('video-view').classList.toggle('active',videoMode);
 if(!videoMode)$('inspection-video').pause();
}
function drawMap(){
 const ns='http://www.w3.org/2000/svg',group=$('map-robots');group.replaceChildren();
 const demo=mode==='demo';$('demo-layout').hidden=!demo;$('demo-layout').style.display=demo?'':'none';$('map-title').textContent=demo?'Demo floor':'Selected robot odometry';$('map-label').textContent=demo?'SIMULATED POSITIONS':'LOCAL FRAME · METRES';
 for(const r of (demo?[...records.values()]:[record()])){
  const s=state(r);if(!fresh(s)||s.x===null||s.y===null)continue;
  const x=demo?35+s.x*42:300+s.x*30,y=demo?235-s.y*30:130-s.y*30;
  if(x<12||x>570||y<15||y>247)continue;
  const g=document.createElementNS(ns,'g'),circle=document.createElementNS(ns,'circle'),text=document.createElementNS(ns,'text');g.setAttribute('transform',`translate(${x},${y})`);
  circle.setAttribute('r',r.robot.id===selected?'13':'8');circle.setAttribute('fill',r.robot.id===selected?'#54daca':'#395775');circle.setAttribute('stroke','#9beddf');
  text.setAttribute('x','18');text.setAttribute('y','4');text.textContent=r.robot.short;g.append(circle,text);group.append(g);
 }
}
function render(){
 renderCockpit();
 $('connection-count').textContent=`${[...records.values()].filter(r=>r.config).length} / 6 CONFIGURED`;
 for(const item of records.values()){
  const card=document.querySelector(`[data-connection="${item.robot.id}"]`);
  card.querySelector('.connection-status').textContent=item.connecting?'Connecting…':!item.config?'Not configured':mode==='demo'?'Paused · demo mode':fresh(item.state)?(item.state.mock?'Bridge simulation':'Connected'):'Offline / stale';
  card.querySelector('[type=submit]').textContent=item.connecting?'Connecting…':item.config?'Reconnect':'Connect';
  card.querySelectorAll('button').forEach(b=>b.disabled=!!item.connecting||transition);
  card.querySelector('[data-disconnect]').disabled=!item.config||!!item.connecting||transition;
 }
 const r=record(),s=state(r),ok=fresh(s);const live=mode==='connected';
 $('mode-label').textContent=live?'CONNECTED SESSION':'DEMO SESSION';$('clock').textContent=new Date().toLocaleTimeString('en-GB');
 for(const item of records.values()){
  const button=document.querySelector(`[data-robot="${item.robot.id}"]`),v=state(item),up=fresh(v);button.classList.toggle('selected',item===r);button.setAttribute('aria-current',item===r?'true':'false');
  button.querySelector('small span').textContent=!live?'Demo · simulated':!item.config?'Not configured':up?(v.mock?'Bridge simulation':'Connected'):'Offline / stale';button.querySelector('i').classList.toggle('online',up);
 }
 $('robot-status').textContent=!live?'SIMULATED':!r.config?'NOT CONNECTED':ok?(s.mock?'BRIDGE SIMULATION':'CONNECTED'):'STALE / OFFLINE';
 $('battery').textContent=ok?fmt(s.battery,' %'):'—';$('voltage').textContent=ok&&s.voltage!==null?fmt(s.voltage,' V',1):'Battery level unavailable';
 $('speed').textContent=ok?fmt(s.vx===null?null:Math.abs(s.vx),' m/s',2):'—';$('speed-note').textContent=!live?'Simulated velocity':r.robot.id==='robot-ar'?'Commanded base velocity':'Reported base velocity';
 $('latency').textContent=ok?fmt(s.latency,' ms'):'—';$('temperature').textContent=ok?fmt(s.temp,' °C'):'—';
 $('freshness').textContent=!live?'Simulated round-trip':!r.config?'No adaptor configured':ok?`Updated ${Math.max(0,(Date.now()-s.received)/1000).toFixed(1)} s ago`:'Telemetry unavailable or stale';
 $('control-state').textContent=r.authorized&&s.enabled?'Manual control enabled':'Control disabled';$('authority').textContent=r.authorized&&s.enabled?'MANUAL':'LOCKED';
 $('enable').textContent=r.busy?'Waiting for acknowledgement…':r.authorized?'Disable control':'Enable control';$('enable').disabled=transition||r.busy||!ok||!s.capabilities.drive;
 document.querySelectorAll('[data-drive]').forEach(b=>b.disabled=!canDrive(r));$('stop-selected').disabled=!configured(r);
 $('drive-hint').textContent=!live?'Enable, then hold a direction to move.':!r.config?'Configure this robot’s adaptor to connect.':!ok?'Fresh telemetry required for control.':!s.capabilities.drive?'Base motion unavailable from this adaptor.':'Enable, then hold to send base commands.';
 $('health').textContent=!live?'Simulation running':!r.config?'Awaiting adaptor':ok?(s.mock?'Bridge simulation':'Telemetry current'):'Stale / disconnected';
 $('pose-x').textContent=ok?fmt(s.x,' m',2):'—';$('pose-y').textContent=ok?fmt(s.y,' m',2):'—';$('pose-yaw').textContent=ok?fmt(s.yaw===null?null:s.yaw*180/Math.PI,'°',1):'—';
 const joints=live?s.joints:($('arm-side').value==='left'?r.leftJoints:r.rightJoints);$('joints').replaceChildren();
 for(let i=0;i<6;i++){const d=document.createElement('div');const label=document.createElement('span'),value=document.createElement('b');label.textContent=`J${i+1}`;value.textContent=fmt(ok?joints[i]:null,live?' rad':'°',live?2:0);d.append(label,value);$('joints').append(d);}
 $('gripper').value=s.gripper??58;$('lift').value=s.lift??0;$('gripper-value').textContent=fmt(s.gripper,' mm');$('lift-value').textContent=fmt(s.lift,' mm');
 const toolsEnabled=!live&&r.authorized;document.querySelectorAll('[data-preset],[data-posture],#gripper,#lift').forEach(b=>b.disabled=!toolsEnabled);
 $('tools-label').textContent=live?'TELEMETRY ONLY':'DEMO CONTROLS';$('tool-note').textContent=live?'Arm, lift and posture commands await validated robot-specific adaptors.':'Demo joint values illustrate the interface, not calibrated hardware limits.';
 $('camera-status').textContent='Camera offline';$('view-caption').textContent='Reference · not live';
 const pts=r.history.map((v,i)=>`${i*500/59},${135-Math.min(v,.25)/.25*110}`).join(' ');$('speed-line').setAttribute('points',pts);
 $('session-note').textContent=live?'Commands go only to explicitly configured adaptors.':'Simulated telemetry · no robot commands';$('footer-summary').textContent=`6 platforms · ${live?[...records.values()].filter(i=>i.config&&fresh(i.state)).length+' fresh connections':'demonstration session'}`;
 drawMap();
}
async function poll(r){
 if(!r.config||r.polling||mode!=='connected')return;
 const version=r.version,config=r.config;r.polling=true;
 try{
  const start=performance.now(),raw=await jsonRequest(config.endpoint+(config.kind==='robot-ar'?'/state':'/argus/v1/state'),{token:config.token});
  if(version!==r.version||mode!=='connected')return;
  const next=config.kind==='robot-ar'?normalizeAR(raw,performance.now()-start):normalizeGeneric(raw,r.robot.id,performance.now()-start);
  r.state=next;r.lastError='';
  if(!fresh(next)&&r.authorized){r.authorized=false;await halt(r,true);log(`${r.robot.name}: stale device telemetry; control locked.`,true);}
 }catch(e){
  if(version!==r.version)return;
  r.state.connected=false;
  if(r.lastError!==e.message){log(`${r.robot.name}: ${e.message}`,true);r.lastError=e.message;}
  if(r.authorized||hold?.id===r.robot.id)await halt(r,true);
 }finally{r.polling=false;render();}
}
function fillConnection(){
 const r=records.get($('connection-robot').value);$('endpoint').value=r.config?.endpoint||'';$('token').value=r.config?.token||'';$('connection-error').textContent='';
 if(!r.config&&r.robot.id==='robot-ar'&&location.pathname.startsWith('/cockpit/'))$('endpoint').value=location.origin;
 $('adapter-note').textContent=r.robot.id==='robot-ar'?'Robot-AR: uses the existing /state, /cmd_vel, /motor and /stop endpoints.':'Requires an ARGUS v1 adaptor. No hardware bridge for this robot is currently included in the repository.';
}
$('connections').onclick=()=>{$('connection-robot').value=selected;fillConnection();$('connection-dialog').showModal();};$('close-connections').onclick=()=>$('connection-dialog').close();$('connection-robot').onchange=fillConnection;
$('connection-form').onsubmit=async event=>{
 event.preventDefault();const r=records.get($('connection-robot').value),button=event.submitter;button.disabled=true;$('connection-error').textContent='';
 try{await connectRobot(r,$('endpoint').value,$('token').value);$('connection-dialog').close();}catch(e){$('connection-error').textContent=`Could not connect: ${e.message}`;}finally{button.disabled=false;render();}
};
async function connectRobot(r,address,accessToken){
 if(r.connecting||transition)throw Error('A connection change is already in progress.');
 r.connecting=true;render();
 try{
  const endpoint=validateEndpoint(address,location.protocol),token=accessToken,kind=r.robot.id==='robot-ar'?'robot-ar':'argus-v1';
  // Probe without sending any actuator commands.
  const start=performance.now(),raw=await jsonRequest(endpoint+(kind==='robot-ar'?'/state':'/argus/v1/state'),{token});
  const next=kind==='robot-ar'?normalizeAR(raw,performance.now()-start):normalizeGeneric(raw,r.robot.id,performance.now()-start);
  if(mode==='demo')await changeMode('connected');else if(r.config)await halt(r,true);
  r.version++;r.config={endpoint,token,kind};r.state=next;r.authorized=false;r.history=[];
  const config=r.config;r.channel=new CommandChannel(async(action,payload)=>{const [path,body]=commandRequest(config.kind,action,payload);return jsonRequest(config.endpoint+path,{method:'POST',body,token:config.token});});
  document.querySelector(`[data-connection="${r.robot.id}"] input`).value=endpoint;
  document.querySelector(`[data-connection="${r.robot.id}"] .connection-card-error`).textContent='';
  await selectRobot(r.robot.id);log(`${r.robot.name}: telemetry connected (${next.mock?'bridge simulation':'hardware report'}). Control remains disabled.`);notice('Telemetry connection established. Enable control explicitly to operate this robot.');
 }finally{r.connecting=false;render();}
}
async function disconnectRobot(r){if(r.connecting)return;await halt(r,true);r.version++;r.config=null;r.channel=null;r.state=emptyState();r.history=[];log(`${r.robot.name}: disconnected.`);fillConnection();render();}
$('disconnect').onclick=()=>disconnectRobot(records.get($('connection-robot').value));
async function changeMode(next){
 if(mode===next||transition)return;transition=true;render();await stopAll();mode=next;$('mode').value=next;for(const r of records.values()){r.authorized=false;r.history=[];r.version++;}transition=false;
 notice(mode==='demo'?'Demo mode: explore the controls with simulated robots. Nothing is sent to hardware.':'Connected mode: configure robot adaptors to receive telemetry. Missing data stays unavailable.');log(`Data source changed to ${mode}. All local controls locked.`);render();
}
$('mode').onchange=()=>changeMode($('mode').value);
$('enable').onclick=async()=>{
 const r=record();if(r.busy)return;r.busy=true;render();
 try{if(r.authorized)await halt(r,true);else{
  if(!fresh(state(r))||!state(r).capabilities.drive)throw Error('Current drive telemetry is required');
  const epoch=r.controlEpoch,source=mode;await send(r,'enable',{enabled:true});
  if(epoch!==r.controlEpoch||selected!==r.robot.id||mode!==source||transition||$('pane-control').hidden){await halt(r,true,true);return;}
  r.authorized=true;if(mode==='demo')r.demo.enabled=true;
  log(`${r.robot.name}: ${mode==='demo'?'demo':'bridge'} control enabled.`);
 }}catch(e){r.authorized=false;notice(e.message,true);log(`${r.robot.name}: enable failed — ${e.message}`,true);await halt(r,true,true);}finally{r.busy=false;render();}
};
async function motionTick(){
 if(!hold||hold.sending)return;
 const active=hold,r=records.get(active.id);if(!canDrive(r)){await halt(r,true);return;}
 active.sending=true;
 try{await send(r,'drive',active.velocity);}catch(e){log(`${r.robot.name}: motion command failed — ${e.message}`,true);await halt(r,true);}finally{active.sending=false;}
}
document.querySelectorAll('[data-drive]').forEach(button=>{
 button.addEventListener('pointerdown',event=>{if(event.button!==0||hold||!canDrive(record()))return;event.preventDefault();button.setPointerCapture(event.pointerId);const limit=Number($('speed-limit').value),d=button.dataset.drive;hold={id:selected,pointerId:event.pointerId,sending:false,velocity:{vx:d==='forward'?limit:d==='back'?-limit:0,wz:d==='left'?.45:d==='right'?-.45:0}};button.classList.add('held');motionTick();});
 for(const type of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(type,()=>{if(hold)halt(records.get(hold.id),false,true);});
});
window.addEventListener('pointerup',()=>{if(hold)halt(records.get(hold.id),false,true);});
window.addEventListener('blur',()=>{for(const r of records.values())if(r.authorized)halt(r,true);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const r of records.values())if(r.authorized)halt(r,true);});
window.addEventListener('pagehide',()=>{for(const r of records.values())if(r.authorized)halt(r,true);});
document.addEventListener('keydown',event=>{
 if($('connection-dialog').open||['INPUT','SELECT','TEXTAREA'].includes(event.target.tagName))return;
 if(event.code==='Space'){event.preventDefault();halt(record(),true);return;}
 const directions={KeyW:'forward',KeyS:'back',KeyA:'left',KeyD:'right'},d=directions[event.code];
 if(!d||event.repeat||event.ctrlKey||event.metaKey||event.altKey||hold||!canDrive(record()))return;
 event.preventDefault();const limit=Number($('speed-limit').value);
 hold={id:selected,key:event.code,sending:false,velocity:{vx:d==='forward'?limit:d==='back'?-limit:0,wz:d==='left'?.45:d==='right'?-.45:0}};
 document.querySelector(`[data-drive="${d}"]`).classList.add('held');motionTick();
});
document.addEventListener('keyup',event=>{if(hold?.key===event.code){event.preventDefault();halt(records.get(hold.id),false,true);}});
$('stop-selected').onclick=()=>halt(record(),true);$('stop-all').onclick=stopAll;
$('speed-limit').oninput=()=>{$('limit-value').textContent=`${Number($('speed-limit').value).toFixed(2)} m/s`;if(hold)halt(records.get(hold.id),false,true);};
$('preview-view').onclick=()=>{videoMode=false;showView();};$('video-view').onclick=()=>{videoMode=true;showView();};
$('arm-side').onchange=render;
document.querySelectorAll('[data-preset]').forEach(button=>button.onclick=()=>{const r=record();if(mode!=='demo'||!r.authorized)return;const values=button.dataset.preset==='home'?[0,0,0,0,0,0]:[15,-30,55,0,25,0];r[$('arm-side').value+'Joints']=values;log(`${r.robot.name}: simulated ${$('arm-side').value} arm ${button.dataset.preset} pose.`);render();});
for(const name of ['gripper','lift']){$(name).oninput=()=>{if(mode!=='demo'||!record().authorized)return;record().demo[name]=Number($(name).value);$(name+'-value').textContent=`${$(name).value} mm`;};$(name).onchange=()=>log(`${record().robot.name}: simulated ${name} ${$(name).value} mm.`);}
document.querySelectorAll('[data-posture]').forEach(button=>button.onclick=()=>{if(mode!=='demo'||!record().authorized)return;record().demo.task=button.dataset.posture;log(`${record().robot.name}: simulated ${button.dataset.posture.toLowerCase()} posture.`);});
$('clear-log').onclick=()=>{logs.length=0;$('events').replaceChildren();};
$('export').onclick=()=>{const snapshot={exported_at:new Date().toISOString(),source:mode,cockpit:cockpitSnapshot(),robots:[...records.values()].map(r=>({id:r.robot.id,name:r.robot.name,state:state(r),fresh:fresh(state(r)),history:r.history})),events:logs};const url=URL.createObjectURL(new Blob([JSON.stringify(snapshot,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='argus-telemetry.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);log('Telemetry snapshot exported. Connection tokens are excluded.');};
$('mobile-robot').onchange=()=>selectRobot($('mobile-robot').value);
document.addEventListener('cockpit-view-change',e=>{if(e.detail!=='control'){if(hold)halt(records.get(hold.id),true);else if(record().authorized||record().busy)halt(record(),true);$('inspection-video').pause();}});
buildFleet();updateSelection();log('ARGUS ready. Demo mode.');render();
setInterval(motionTick,150);
setInterval(()=>{
 for(const r of records.values()){
  const s=state(r);if(mode==='demo'){s.received=Date.now();s.sourceAge=0;s.x=clamp(s.x+Math.cos(s.yaw)*s.vx*.25,.2,12);s.y=clamp(s.y+Math.sin(s.yaw)*s.vx*.25,.2,7);s.yaw+=s.wz*.25;}
  if(r.authorized&&!fresh(s)){r.authorized=false;halt(r,true);}
 }
 render();
},250);
setInterval(()=>{for(const r of records.values()){const s=state(r);if(fresh(s)&&s.vx!==null){r.history.push(Math.abs(s.vx));if(r.history.length>60)r.history.shift();}else r.history=[];poll(r);}},1000);
