// Keep device setup, cockpit hardware and operating controls in separate views.
const main=document.querySelector('main');
const tabs=document.createElement('nav');tabs.className='workspace-tabs';tabs.setAttribute('aria-label','Workspace');tabs.setAttribute('role','tablist');
const sections={};
for(const [id,label] of [['control','Control'],['devices','Devices'],['cockpit','Cockpit'],['activity','Activity']]){
 const button=document.createElement('button');button.type='button';button.id=`tab-${id}`;button.textContent=label;button.dataset.view=id;button.setAttribute('role','tab');button.setAttribute('aria-controls',`pane-${id}`);tabs.append(button);
 const section=document.createElement('section');section.id=`pane-${id}`;section.className='workspace-pane';section.setAttribute('role','tabpanel');section.setAttribute('aria-labelledby',button.id);sections[id]=section;
}
document.querySelector('.workspace-head').after(tabs);
tabs.after(...Object.values(sections));
tabs.after(document.getElementById('notice'));
sections.control.append(document.querySelector('.stats'));
const controls=document.createElement('div');controls.className='main-grid operating-grid';controls.append(document.querySelector('.vision'),document.querySelector('.drive'));sections.control.append(controls);
const advanced=document.createElement('details');advanced.className='advanced-telemetry';advanced.innerHTML='<summary>Robot tools &amp; detailed telemetry</summary>';
const detailGrid=document.createElement('div');detailGrid.className='main-grid';detailGrid.append(document.querySelector('.tools'),document.querySelector('.position'),document.querySelector('.signal'));advanced.append(detailGrid);sections.control.append(advanced);
sections.devices.append(document.querySelector('.robot-connections'));
sections.cockpit.append(document.querySelector('.cockpit-status'));
sections.activity.append(document.querySelector('.events'));
const exportButton=document.createElement('button');exportButton.type='button';exportButton.className='text-button';exportButton.textContent='Export telemetry';exportButton.onclick=()=>document.getElementById('export').click();document.querySelector('.events .panel-head').append(exportButton);
document.querySelector('main > .main-grid')?.remove();
const connect=document.createElement('button');connect.id='selected-connect';connect.type='button';connect.textContent='Connect robot';connect.onclick=()=>document.getElementById('connections').click();document.querySelector('.head-actions').prepend(connect);
const summary=document.createElement('button');summary.className='cockpit-chip';summary.type='button';summary.textContent='Cockpit · hardware not linked';summary.onclick=()=>showView('cockpit');document.querySelector('.sidebar .rail-bottom').prepend(summary);
const picker=document.createElement('select');picker.id='mobile-robot';picker.setAttribute('aria-label','Select robot');document.querySelector('.sidebar').prepend(picker);
document.querySelector('.rail-title span').textContent='MY ROBOTS';
document.querySelector('.rail-note').remove();
document.getElementById('connections').textContent='+ Connection settings';
document.querySelector('.wordmark small').textContent='STUDIO';
document.getElementById('mode').options[0].textContent='Demo';document.getElementById('mode').options[1].textContent='Live';
document.querySelector('.mode-picker').firstChild.textContent='Mode';
document.querySelector('.drive .micro').textContent='Hold W/A/S/D or a direction. Release to halt. Space = stop. Software stop only.';
document.querySelector('.vision h2').textContent='Robot view';
document.querySelector('.events h2').textContent='Activity';
document.querySelector('.robot-connections .cockpit-status-note').textContent='Connect telemetry here, then enable motion in Control. Robot-AR has a bridge; other robots need an adaptor.';
document.querySelector('.cockpit-status-note').textContent='These checks verify software behavior, not robot hardware. Leader arms, pedals, headset sessions, physical stop feedback and on-site route reliability remain unverified.';
document.getElementById('view-caption').textContent='Reference · not live';
document.getElementById('notice').textContent='Demo mode · no hardware commands.';
function showView(id){
 for(const [key,pane] of Object.entries(sections)){pane.hidden=key!==id;const button=document.getElementById(`tab-${key}`);button.classList.toggle('active',key===id);button.setAttribute('aria-selected',String(key===id));button.tabIndex=key===id?0:-1;}
 document.dispatchEvent(new CustomEvent('cockpit-view-change',{detail:id}));
}
tabs.addEventListener('click',e=>{if(e.target.dataset.view)showView(e.target.dataset.view);});
tabs.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const buttons=[...tabs.children];let i=buttons.indexOf(document.activeElement);i=e.key==='Home'?0:e.key==='End'?buttons.length-1:(i+(e.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;showView(buttons[i].dataset.view);buttons[i].focus();});
document.addEventListener('cockpit-select-robot',()=>showView('control'));
showView('control');
