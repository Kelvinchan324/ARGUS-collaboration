// Run against an isolated HTTP fixture, never robot hardware.
// PLAYWRIGHT_MODULE: optional absolute module path; BROWSER_CHANNEL: e.g. msedge.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const root=path.resolve(__dirname,'../../build/pages-control');
const out=path.resolve(__dirname,'../../build/cockpit-qa');fs.mkdirSync(out,{recursive:true});
let enabled=false,stale=false,failStop=false,enableDelay=0;
const commands=[];
const fixture=http.createServer(async(req,res)=>{
 if(req.url.startsWith('/adaptor/')){
  const robotId=req.url.split('/')[2];res.setHeader('Content-Type','application/json');
  if(req.method==='GET')res.end(JSON.stringify({protocol:'argus.v1',robot_id:robotId,mode:'simulation',sample_time_ms:Date.now(),connected:true,motor_enabled:false,watchdog_ms:500,capabilities:{drive:true},telemetry:{vx:0,x:0,y:0,yaw:0}}));
  else res.end(JSON.stringify({ok:true}));return;
 }
 if(req.url.startsWith('/bridge/')){
  res.setHeader('Content-Type','application/json');
  if(req.url==='/bridge/state'){res.end(JSON.stringify({chassis:{mock:true,connected:false,motor_enabled:enabled,last_rx_age_s:stale?10:.01,voltage:24,vx:0,wz:0,odom_x:0,odom_y:0,odom_th:0},arms:{left:{joints:[0,0,0,0,0,0]}},capabilities:{chassis:{wired:false}}}));return;}
  let body='';for await(const chunk of req)body+=chunk;
  const data=JSON.parse(body||'{}');commands.push({url:req.url,data});
  if(req.url==='/bridge/motor'){if(enableDelay)await new Promise(r=>setTimeout(r,enableDelay));enabled=data.enabled;}
  if(req.url==='/bridge/stop'){if(failStop){res.writeHead(503);res.end(JSON.stringify({ok:false}));return;}enabled=false;}
  res.end(JSON.stringify({ok:true}));return;
 }
 if(req.url==='/wrong/argus/v1/state'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({protocol:'argus.v1',robot_id:'wrong-robot',mode:'hardware',sample_time_ms:Date.now()}));return;}
 let rel=decodeURIComponent(req.url.split('?')[0]);if(rel.endsWith('/'))rel+='index.html';
 const file=path.resolve(root,'.'+rel);
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',({'.html':'text/html','.mjs':'application/javascript','.js':'application/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.gif':'image/gif','.mp4':'video/mp4'})[path.extname(file)]||'application/octet-stream');
 fs.createReadStream(file).pipe(res);
});
(async()=>{
 await new Promise(r=>fixture.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${fixture.address().port}`;
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{})});
 try{
  const errors=[];
  const site=await browser.newPage({viewport:{width:1536,height:1080}});
  site.on('pageerror',e=>errors.push(e.message));
  await site.goto(origin+'/');await site.waitForSelector('#pilot');
  assert.equal(await site.locator('.pilot-metrics article').count(),4);
  const projectLinks=await site.locator('.robot-card a[target="_blank"]').evaluateAll(links=>links.map(link=>link.href));
  assert.deepEqual(projectLinks,[
   'https://github.com/liyiteng/AlohaMini',
   'https://github.com/dimensionalOS/dimos/blob/main/docs/platforms/quadruped/go2/setup.md',
   'https://github.com/Nate711/pupperv3-monorepo',
   'https://github.com/apirrone/Open_Duck_Mini/tree/v2'
  ]);
  assert.match(await site.locator('.fleet-section .section-heading>p').textContent(),/illustrative/i);
  assert.match(await site.locator('.pilot-boundary').textContent(),/does not certify compliance/i);
  assert.equal((await site.locator('a[href="ARGUS-Safety-Report-2026.pdf"]').textContent()).trim(),'Draft event safety plan');
  const safety=await site.request.get(origin+'/ARGUS-Safety-Report-2026.pdf');assert.equal(safety.status(),200);assert((await safety.body()).length>10000);
  const conceptVideo=await site.request.get(origin+'/connected-robots/bimanual-bunker-mini/media/Industrial_Inspection_Demo.mp4');assert.equal(conceptVideo.status(),200);assert((await conceptVideo.body()).length>100000);
  for(const image of await site.locator('img').all()){await image.scrollIntoViewIfNeeded();await image.evaluate(img=>img.complete&&img.naturalWidth>0?true:new Promise((resolve,reject)=>{img.addEventListener('load',()=>resolve(true),{once:true});img.addEventListener('error',()=>reject(Error(`Image failed: ${img.src}`)),{once:true});}));}
  await site.setViewportSize({width:390,height:844});
  assert.equal(await site.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await site.close();
  const page=await browser.newPage({viewport:{width:1536,height:1080}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/control/');await page.waitForSelector('.robot-option');
  assert.equal(await page.locator('.robot-option').count(),6);assert.equal(commands.length,0);
  assert.equal(await page.locator('.robot-connection-card').count(),6);
  assert.equal(await page.locator('#pane-devices').isVisible(),false);
  assert.equal(await page.locator('#pane-cockpit').isVisible(),false);
  assert.equal(await page.locator('.argus-logo').evaluate(img=>img.complete&&img.naturalWidth>0),true);
  assert.equal(await page.locator('.cockpit-status-grid article').count(),8);
  assert.equal(await page.locator('.verification-grid article').count(),4);
  assert.match(await page.locator('.cockpit-status-note').first().textContent(),/not robot hardware/);
  assert.equal(await page.locator('#cockpit-readiness').textContent(),'HARDWARE UNVERIFIED');
  await page.locator('#enable').click();
  const forward=page.locator('[data-drive=forward]');await forward.hover();await page.mouse.down();await page.waitForTimeout(650);
  assert.equal(await page.locator('#route-status').textContent(),'Demo control enabled');
  assert.notEqual(await page.locator('#speed').textContent(),'0.00 m/s');await page.mouse.up();await page.waitForTimeout(300);assert.equal(await page.locator('#speed').textContent(),'0.00 m/s');assert.equal(commands.length,0);
  await page.keyboard.down('w');await page.waitForTimeout(350);assert.notEqual(await page.locator('#speed').textContent(),'0.00 m/s');await page.keyboard.up('w');await page.waitForTimeout(300);assert.equal(await page.locator('#speed').textContent(),'0.00 m/s');
  await page.locator('.advanced-telemetry summary').click();await page.locator('[data-preset=inspect]').click();assert.match(await page.locator('#joints').textContent(),/55/);await page.locator('.advanced-telemetry summary').click();
  await page.locator('#stop-all').click();await page.waitForFunction(()=>document.querySelector('[data-drive=forward]').disabled);
  await page.locator('#enable').click();await page.locator('#tab-cockpit').click();await page.waitForFunction(()=>document.querySelector('#route-status').textContent==='Control locked');assert.equal(await page.locator('#pane-cockpit').isVisible(),true);await page.locator('#tab-control').click();
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  for(const id of ['robot-ar','aloha-mini','unitree-go2','pupper-v3','open-duck-mini','bimanual-bunker-mini']){await page.locator(`[data-robot="${id}"]`).click();await page.waitForFunction(id=>document.querySelector(`[data-robot="${id}"]`).getAttribute('aria-current')==='true',id);await page.waitForFunction(()=>{const img=document.querySelector('#robot-image');return img.complete&&img.naturalWidth>0;});assert.equal(await page.locator('#robot-image').evaluate(img=>getComputedStyle(img).objectFit),'contain');}
  await page.locator('#video-view').click();assert.equal(await page.locator('#inspection-video').isVisible(),true);await page.locator('#preview-view').click();
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.setViewportSize({width:1536,height:1080});
  await page.locator('#connections').click();await page.locator('#connection-robot').selectOption('robot-ar');await page.locator('#endpoint').fill(origin+'/bridge');await page.locator('#token').fill('test-only-token');await page.locator('#connection-form button[type=submit]').click();await page.waitForFunction(()=>!document.querySelector('#connection-dialog').open);
  assert.equal(await page.locator('#mode').inputValue(),'connected');assert.match(await page.locator('#robot-status').textContent(),/SIMULATION/);assert.equal(commands.length,0);assert.equal(await page.locator('#battery').textContent(),'—');assert.equal(await page.locator('#gripper').isDisabled(),true);
  assert.equal(await page.locator('#links-status').textContent(),'1 / 6 fresh links');
  assert.equal(await page.locator('#vr-status').textContent(),'Not connected');
  assert.equal(await page.locator('#cockpit-readiness').textContent(),'HARDWARE UNVERIFIED');
  await page.locator('#enable').click();await page.waitForFunction(()=>!document.querySelector('[data-drive=forward]').disabled);await forward.hover();await page.mouse.down();await page.waitForTimeout(550);await page.mouse.up();await page.waitForTimeout(300);
  assert(commands.some(c=>c.url.endsWith('/cmd_vel')&&c.data.vx>0));assert.equal(commands.at(-1).data.vx,0);
  // Export includes no bearer token or connection configuration.
  const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;await download.saveAs(path.join(out,'export.json'));assert(!fs.readFileSync(path.join(out,'export.json'),'utf8').includes('test-only-token'));
  stale=true;await page.waitForFunction(()=>document.querySelector('#authority').textContent==='LOCKED');assert.equal(await forward.isDisabled(),true);assert(commands.some(c=>c.url.endsWith('/stop')));stale=false;
  await page.waitForFunction(()=>!document.querySelector('#enable').disabled);failStop=true;await page.locator('#stop-selected').click();await page.waitForFunction(()=>document.querySelector('#events').textContent.includes('STOP NOT CONFIRMED'));failStop=false;
  // Switching away during a pending enable must not leave that robot armed.
  enableDelay=500;await page.locator('#enable').click();await page.locator('[data-robot=bimanual-bunker-mini]').click();await page.waitForFunction(()=>document.querySelector('#robot-code').textContent==='BM');await page.waitForTimeout(900);assert.equal(enabled,false);enableDelay=0;
  // Identity validation rejects a response from the wrong robot.
  await page.locator('#connections').click();await page.locator('#connection-robot').selectOption('pupper-v3');await page.locator('#endpoint').fill(origin+'/wrong');await page.locator('#connection-form button[type=submit]').click();await page.waitForFunction(()=>document.querySelector('#connection-error').textContent.includes('identity'));await page.locator('#close-connections').click();
  for(const id of ['bimanual-bunker-mini','aloha-mini','unitree-go2','pupper-v3','open-duck-mini']){
   await page.locator('#tab-devices').click();
   const card=page.locator(`[data-connection="${id}"]`);await card.locator('input').fill(origin+'/adaptor/'+id);await card.locator('[type=submit]').click();await page.waitForFunction(id=>document.querySelector(`[data-connection="${id}"] .connection-status`).textContent==='Bridge simulation',id);
  }
  assert.equal(await page.locator('#connection-count').textContent(),'6 / 6 CONFIGURED');
  await page.locator('#tab-devices').click();await page.locator('[data-connection=pupper-v3] [data-disconnect]').click();await page.waitForFunction(()=>document.querySelector('#connection-count').textContent==='5 / 6 CONFIGURED');
  assert.equal(await page.locator('[data-connection=unitree-go2] .connection-status').textContent(),'Bridge simulation');
  assert.equal(errors.length,0,errors.join('\n'));
  console.log(JSON.stringify({robots:6,projectLinks:projectLinks.length,safetyReport:true,conceptVideo:true,demoSendsNoCommands:true,holdRelease:true,staleLock:true,failedStopReported:true,pendingEnableCancelled:true,wrongIdentityRejected:true,exportExcludesToken:true,mobileOverflow:false,pageErrors:errors.length,commands:commands.length}));
 }finally{await browser.close();fixture.close();}
})().catch(e=>{console.error(e);fixture.close();process.exitCode=1;});
