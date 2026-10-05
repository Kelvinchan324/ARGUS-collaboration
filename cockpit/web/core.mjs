export const ROBOTS = [
  {id:'bimanual-bunker-mini',name:'Bimanual Bunker Mini',short:'BM',kind:'Tracked · dual arm',arms:true,lift:true,status:'Inspection concept',image:'../assets/generated/bunker-mini-studio.jpg'},
  {id:'robot-ar',name:'Robot-AR',short:'AR',kind:'Wheeled · four arm',arms:true,status:'Bridge prototype',image:'../assets/generated/robot-ar-studio.jpg'},
  {id:'aloha-mini',name:'Aloha Mini',short:'AM',kind:'Wheeled · dual arm',arms:true,status:'Adaptor not verified',image:'../assets/generated/aloha-mini-studio.jpg'},
  {id:'unitree-go2',name:'Unitree Go2',short:'G2',kind:'Quadruped · inspection',legs:true,status:'dimOS path identified',image:'../assets/fleet/unitree-go2.jpg'},
  {id:'pupper-v3',name:'Pupper V3',short:'P3',kind:'Quadruped · research',legs:true,status:'Adaptor not verified',image:'../assets/fleet/pupper-v3.jpg'},
  {id:'open-duck-mini',name:'Open Duck Mini v2',short:'OD',kind:'Biped · research',legs:true,status:'Adaptor not verified',image:'../assets/fleet/open-duck-mini-v2.png'},
];
export const STALE_MS=2500;
export const finite = v => typeof v==='number' && Number.isFinite(v) ? v : null;
export const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
export function emptyState(){return {connected:false,mock:false,enabled:false,battery:null,voltage:null,vx:null,wz:null,x:null,y:null,yaw:null,temp:null,latency:null,received:0,sourceAge:0,capabilities:{},joints:[],task:'No telemetry',camera:null};}
export function demoState(robot,index){return {...emptyState(),connected:true,mock:true,battery:92-index*7,voltage:25-index*.2,vx:0,wz:0,x:1.5+index*1.6,y:2+(index%2)*2.8,yaw:0,temp:36+index,latency:12+index*3,received:Date.now(),capabilities:{drive:true,arms:!!robot.arms,lift:!!robot.lift,posture:!!robot.legs},joints:robot.arms?[0,-12,24,0,12,0]:[],gripper:58,lift:0,task:'Standby',sample:true};}
export function fresh(s,now=Date.now()){return s.connected && now-s.received+s.sourceAge<STALE_MS;}
export function normalizeAR(raw,latency,now=Date.now()){
 const c=raw?.chassis;
 if(!c || typeof c.mock!=='boolean' || typeof c.connected!=='boolean')throw Error('Not a Robot-AR bridge state');
 const s=emptyState();
 Object.assign(s,{connected:c.connected||c.mock,mock:c.mock,enabled:c.motor_enabled===true,voltage:finite(c.voltage),vx:finite(c.vx),wz:finite(c.wz),x:finite(c.odom_x),y:finite(c.odom_y),yaw:finite(c.odom_th),received:now,latency,
 sourceAge:finite(c.last_rx_age_s)!==null?Math.max(0,c.last_rx_age_s*1000):Infinity,
 task:raw.task?.status||'No active task',joints:Array.isArray(raw.arms?.left?.joints)?raw.arms.left.joints.map(finite):[],camera:raw.camera?.frame===true?'frame available':null,
 capabilities:{drive:c.mock||raw.capabilities?.chassis?.wired===true,arms:false,lift:false,posture:false}});
 // The public fleet cockpit keeps hardware arm and lift commands disabled until supervised validation.
 return s;
}
export function normalizeGeneric(raw,robotId,latency,now=Date.now()){
 if(raw?.protocol!=='argus.v1'||raw.robot_id!==robotId||!['hardware','simulation'].includes(raw.mode))throw Error('Adaptor identity or protocol mismatch');
 const timestamp=finite(raw.sample_time_ms);
 if(timestamp===null||timestamp>now+1000)throw Error('Invalid telemetry timestamp');
 const s=emptyState(),t=raw.telemetry||{};
 for(const key of ['battery','voltage','vx','wz','x','y','yaw','temp'])s[key]=finite(t[key]);
 if(s.battery!==null&&(s.battery<0||s.battery>100))s.battery=null;
 Object.assign(s,{connected:raw.connected===true,mock:raw.mode==='simulation',enabled:raw.motor_enabled===true,received:now,sourceAge:Math.max(0,now-timestamp),latency,task:typeof raw.task==='string'?raw.task:'No active task'});
 // This first dashboard version enables only base motion on connected adaptors.
 s.capabilities={drive:raw.capabilities?.drive===true&&raw.watchdog_ms>0&&raw.watchdog_ms<=500,arms:false,lift:false,posture:false};
 return s;
}
export function validateEndpoint(input,pageProtocol='http:'){
 const u=new URL(input);
 if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash)throw Error('Use an HTTP(S) bridge URL without credentials, query or fragment.');
 if(pageProtocol==='https:'&&u.protocol!=='https:')throw Error('This HTTPS page needs an HTTPS bridge. Or open the cockpit locally on the Robot-AR bridge.');
 return u.href.replace(/\/$/,'');
}
export function commandRequest(kind,action,payload={}){
 if(kind==='robot-ar'){
  if(action==='stop')return ['/stop',{}];
  if(action==='enable')return ['/motor',{enabled:payload.enabled===true}];
  if(action==='drive')return ['/cmd_vel',{vx:clamp(payload.vx||0,-.25,.25),vy:0,wz:clamp(payload.wz||0,-.6,.6)}];
  throw Error('This control is not wired for Robot-AR.');
 }
 if(!['stop','enable','drive'].includes(action))throw Error('Unsupported connected control');
 return ['/argus/v1/command',{action,...(action==='drive'?{vx:clamp(payload.vx||0,-.25,.25),wz:clamp(payload.wz||0,-.6,.6)}:payload)}];
}
export async function jsonRequest(url,{method='GET',body,token='',timeout=1300}={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
 try{
  const headers={Accept:'application/json'};
  if(body!==undefined)headers['Content-Type']='application/json';
  if(token)headers.Authorization=`Bearer ${token}`;
  const response=await fetch(url,{method,headers,body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal,cache:'no-store',credentials:'same-origin'});
  if(!response.ok)throw Error(`Bridge returned HTTP ${response.status}`);
  const result=await response.json();
  if(method==='POST'&&result.ok!==true)throw Error('Command was not acknowledged');
  return result;
 }finally{clearTimeout(timer);}
}
// Serialize outbound commands. A stop invalidates queued motion and follows any
// in-flight request; the robot's own watchdog remains the final network safeguard.
export class CommandChannel {
 constructor(send){this.send=send;this.tail=Promise.resolve();this.epoch=0;}
 run(action,payload={},interrupt=false){
  if(interrupt)this.epoch++;
  const epoch=this.epoch;
  const next=this.tail.catch(()=>{}).then(()=>epoch===this.epoch?this.send(action,payload):{skipped:true});
  this.tail=next;return next;
 }
}
