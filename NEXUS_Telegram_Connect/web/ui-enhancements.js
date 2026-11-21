(function(){
"use strict";
if(window.__FOZILBEK_GLOBAL_UI__)return;
window.__FOZILBEK_GLOBAL_UI__=true;
const css=".f-ui-progress{position:fixed;z-index:2147482500;left:0;top:0;height:2px;width:0;background:var(--ui-accent,var(--accent,var(--gold,var(--green,#69cfff))));box-shadow:0 0 12px currentColor;pointer-events:none}"+
".f-ui-search-trigger{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-width:38px;height:38px;padding:0 12px;border:1px solid color-mix(in srgb,var(--ui-accent,var(--accent,var(--gold,#69cfff))) 35%,transparent);border-radius:11px;background:transparent;color:inherit;font:600 12px system-ui;cursor:pointer}"+
".f-ui-search-trigger:hover{border-color:var(--ui-accent,var(--accent,var(--gold,#69cfff)));transform:translateY(-1px)}.f-ui-search-trigger kbd{font:10px ui-monospace,monospace;opacity:.7;border:1px solid currentColor;border-radius:4px;padding:3px 5px}"+
".f-ui-palette{position:fixed;inset:0;z-index:2147482600;display:none;align-items:flex-start;justify-content:center;padding:12vh 18px 24px;background:#02050ab8;backdrop-filter:blur(12px)}.f-ui-palette.is-open{display:flex}"+
".f-ui-palette-card{width:min(620px,100%);max-height:70vh;overflow:hidden;border:1px solid color-mix(in srgb,var(--ui-accent,var(--accent,var(--gold,#69cfff))) 32%,#ffffff18);border-radius:18px;background:var(--panel-solid,var(--panel,#101722));color:var(--text,#edf3ff);box-shadow:0 28px 100px #0009}"+
".f-ui-palette-top{display:flex;align-items:center;gap:12px;padding:16px 18px;border-bottom:1px solid #ffffff20}.f-ui-palette-top span{font-size:18px}.f-ui-palette-input{width:100%;min-width:0;border:0!important;outline:0!important;background:transparent!important;color:inherit!important;font:500 15px system-ui!important;box-shadow:none!important}"+
".f-ui-palette-results{max-height:50vh;overflow:auto;padding:8px}.f-ui-result{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;padding:12px 13px;border:0;border-radius:10px;background:transparent;color:inherit;text-align:left;font:500 13px system-ui;cursor:pointer}.f-ui-result:hover,.f-ui-result:focus-visible{outline:0;background:color-mix(in srgb,var(--ui-accent,var(--accent,var(--gold,#69cfff))) 13%,transparent)}.f-ui-result small,.f-ui-empty{color:var(--muted,#91a0b8);font-size:11px}.f-ui-empty{padding:22px;text-align:center;font-size:13px}"+
".f-ui-snow{position:fixed;inset:0;width:100%;height:100%;z-index:1000;pointer-events:none;opacity:.38}@media(max-width:640px){.f-ui-search-trigger .f-ui-search-label,.f-ui-search-trigger kbd{display:none}.f-ui-search-trigger{width:38px;padding:0}}@media(prefers-reduced-motion:reduce){.f-ui-snow{display:none!important}}";
const st=document.createElement("style");st.id="foz-global-ui-styles";st.textContent=css+".f-ui-section-rail{position:fixed;left:14px;top:50%;transform:translateY(-50%);z-index:999;display:grid;gap:7px;padding:8px;border:1px solid color-mix(in srgb,var(--ui-accent,var(--accent,var(--gold,#69cfff))) 22%,transparent);border-radius:14px;background:color-mix(in srgb,var(--panel-solid,var(--panel,#101722)) 82%,transparent);backdrop-filter:blur(14px)}.f-ui-section-rail a{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;color:var(--muted,#91a0b8);font:700 10px system-ui;text-decoration:none}.f-ui-section-rail a:hover,.f-ui-section-rail a.is-active{color:var(--ui-accent,var(--accent,var(--gold,#69cfff)));background:color-mix(in srgb,var(--ui-accent,var(--accent,var(--gold,#69cfff))) 13%,transparent)}@media(max-width:1180px){.f-ui-section-rail{display:none}}";document.head.appendChild(st);
const bar=document.createElement("div");bar.className="f-ui-progress";document.body.appendChild(bar);
function progress(){const m=document.documentElement.scrollHeight-innerHeight;bar.style.width=(m>0?Math.min(100,scrollY/m*100):0)+"%"}addEventListener("scroll",progress,{passive:true});progress();
const overlay=document.createElement("div");overlay.className="f-ui-palette";overlay.setAttribute("role","dialog");overlay.setAttribute("aria-modal","true");overlay.innerHTML='<div class="f-ui-palette-card"><div class="f-ui-palette-top"><span>⌕</span><input class="f-ui-palette-input" type="search" placeholder="Sahifa, bo‘lim yoki havolani qidiring…" autocomplete="off"><kbd>ESC</kbd></div><div class="f-ui-palette-results" role="listbox"></div></div>';document.body.appendChild(overlay);
const input=overlay.querySelector("input"),list=overlay.querySelector(".f-ui-palette-results");let previousFocus=null;
function close(){overlay.classList.remove("is-open");if(previousFocus&&previousFocus.focus)previousFocus.focus({preventScroll:true})}
function render(){const q=input.value.trim().toLocaleLowerCase();const items=[];document.querySelectorAll("a[href],button,[role='button'],h1,h2,h3,h4,[data-searchable]").forEach(el=>{if(el.closest(".f-ui-palette")||el.closest("script,style")||el.hidden||el.disabled)return;const label=(el.getAttribute("aria-label")||el.innerText||el.textContent||"").replace(/\s+/g," ").trim();if(!label||label.length>110||(q&&!label.toLocaleLowerCase().includes(q)))return;items.push({el,label,type:el.matches("a[href]")?"Havola":el.matches("button,[role='button']")?"Amal":"Bo‘lim"})});list.replaceChildren();items.slice(0,18).forEach(item=>{const b=document.createElement("button");b.className="f-ui-result";b.type="button";const a=document.createElement("span"),s=document.createElement("small");a.textContent=item.label;s.textContent=item.type;b.append(a,s);b.addEventListener("click",()=>{close();if(item.el.matches("a[href]"))item.el.click();else{item.el.scrollIntoView({behavior:"smooth",block:"center"});if(item.el.matches("button,[role='button']"))item.el.focus({preventScroll:true})}});list.appendChild(b)});if(!items.length){const e=document.createElement("div");e.className="f-ui-empty";e.textContent="Mos natija topilmadi.";list.appendChild(e)}}
function open(){previousFocus=document.activeElement;overlay.classList.add("is-open");input.value="";render();input.focus()}
input.addEventListener("input",render);overlay.addEventListener("click",e=>{if(e.target===overlay)close()});document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();open()}if(e.key==="Escape"&&overlay.classList.contains("is-open"))close()});
const trigger=document.createElement("button");trigger.type="button";trigger.className="f-ui-search-trigger";trigger.setAttribute("aria-label","Qidiruvni ochish");trigger.innerHTML='<span>⌕</span><span class="f-ui-search-label">Qidirish</span><kbd>Ctrl K</kbd>';trigger.addEventListener("click",open);const header=document.querySelector("header,.topbar,.app-header");if(header){(header.querySelector(".header-actions,.header-right,.nav-actions")||header).appendChild(trigger)}else{trigger.style.cssText="position:fixed;right:18px;bottom:18px;z-index:1001";document.body.appendChild(trigger)}
function buildSectionRail(){
 const contentRoot=document.querySelector("main")||document.body;
 const sectionHeads=Array.from(contentRoot.querySelectorAll("section h2,section h3,main h2,main h3")).filter(h=>h.textContent.trim()&&!h.closest(".f-ui-palette,[hidden],.hidden")&&getComputedStyle(h).display!=="none");
 const uniqueHeads=sectionHeads.filter((h,i,a)=>a.findIndex(x=>x.textContent.trim()===h.textContent.trim())===i).slice(0,9);
 let rail=document.querySelector(".f-ui-section-rail");
 if(document.querySelector(".sidebar")||uniqueHeads.length<3){if(rail)rail.remove();return}
 if(!rail){rail=document.createElement("nav");rail.className="f-ui-section-rail";rail.setAttribute("aria-label","Sahifa bo‘limlari");document.body.appendChild(rail)}
 rail.replaceChildren();
 uniqueHeads.forEach((h,i)=>{if(!h.id)h.id="f-ui-section-"+(i+1);const a=document.createElement("a");a.href="#"+h.id;a.textContent=String(i+1).padStart(2,"0");a.title=h.textContent.trim();rail.appendChild(a)});
 const links=Array.from(rail.querySelectorAll("a"));
 if(window.IntersectionObserver){const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting)links.forEach(a=>a.classList.toggle("is-active",a.hash==="#"+entry.target.id))}),{rootMargin:"-18% 0px -72% 0px"});uniqueHeads.forEach(h=>observer.observe(h))}
}
buildSectionRail();
const railObserver=new MutationObserver(()=>{if(!document.querySelector(".f-ui-section-rail"))buildSectionRail()});
railObserver.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:["class","hidden"]});
if(!matchMedia("(prefers-reduced-motion:reduce)").matches&&!matchMedia("(pointer:coarse)").matches){const c=document.createElement("canvas");c.className="f-ui-snow";c.setAttribute("aria-hidden","true");document.body.appendChild(c);const x=c.getContext("2d");let w=0,h=0,flakes=[],raf=0;function size(){const d=Math.min(devicePixelRatio||1,1.5);w=innerWidth;h=innerHeight;c.width=w*d;c.height=h*d;c.style.width=w+"px";c.style.height=h+"px";x.setTransform(d,0,0,d,0,0);flakes=Array.from({length:Math.min(55,Math.max(20,Math.floor(w/27)))},()=>({x:Math.random()*w,y:Math.random()*h,r:.7+Math.random()*1.7,s:.25+Math.random()*.5,a:.2+Math.random()*.45}))}function draw(){x.clearRect(0,0,w,h);flakes.forEach(f=>{x.beginPath();x.fillStyle="rgba(235,244,255,"+f.a+")";x.arc(f.x,f.y,f.r,0,Math.PI*2);x.fill();f.y+=f.s;f.x+=Math.sin(f.y*.008)*.22;if(f.y>h+4){f.y=-4;f.x=Math.random()*w}});raf=requestAnimationFrame(draw)}size();addEventListener("resize",size,{passive:true});document.addEventListener("visibilitychange",()=>{if(document.hidden){cancelAnimationFrame(raf);raf=0}else if(!raf)draw()});draw()}

/* Theme-colored arrow pointer: keeps the familiar RoboContest-style pointer shape. */
if(!matchMedia("(pointer:coarse)").matches&&!matchMedia("(prefers-reduced-motion:reduce)").matches){
 const pointer=document.createElement("div");
 pointer.className="f-ui-arrow-pointer";
 pointer.setAttribute("aria-hidden","true");
 pointer.innerHTML='<svg viewBox="0 0 24 32" width="25" height="33" xmlns="http://www.w3.org/2000/svg"><path d="M2 1.5V25l6.1-5.8 4.1 9.1 4.1-1.9-4.2-8.9 8.5-.4L2 1.5Z" fill="currentColor" stroke="#07111f" stroke-width="1.5" stroke-linejoin="round"/></svg>';
 pointer.style.cssText="position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;opacity:0;transform:translate(-2px,-2px);color:var(--ui-accent,var(--accent,var(--gold,var(--green,var(--neon,#69cfff)))));filter:drop-shadow(0 2px 3px #0008);transition:opacity .12s";
 document.body.appendChild(pointer);
 document.documentElement.classList.add("f-ui-custom-cursor");
 const pointerStyle=document.createElement("style");
 pointerStyle.textContent="html.f-ui-custom-cursor,html.f-ui-custom-cursor *{cursor:none!important}.f-ui-arrow-pointer.is-hover svg{transform:scale(1.08);transform-origin:top left}.f-ui-arrow-pointer svg{display:block;transition:transform .12s}";
 document.head.appendChild(pointerStyle);
 document.addEventListener("pointermove",e=>{pointer.style.left=e.clientX+"px";pointer.style.top=e.clientY+"px";pointer.style.opacity="1"},{passive:true});
 document.addEventListener("pointerover",e=>{if(e.target.closest("a,button,[role='button'],input,select,textarea,label"))pointer.classList.add("is-hover");else pointer.classList.remove("is-hover")},{passive:true});
 document.addEventListener("pointerdown",()=>{pointer.style.transform="translate(-2px,-2px) scale(.9)"});
 document.addEventListener("pointerup",()=>{pointer.style.transform="translate(-2px,-2px) scale(1)"});
 document.addEventListener("pointerleave",()=>{pointer.style.opacity="0"});
 document.addEventListener("pointerenter",()=>{pointer.style.opacity="1"});
}


(function(){
"use strict";
const edu=!!document.querySelector("#dashboard"),clim=!!document.querySelector(".module-grid"),nexus=!!document.querySelector("#starCanvas");
const existing=document.querySelector(".sidebar");
const css=[
".f-contest-sidebar{position:fixed;inset:0 auto 0 0;width:258px;z-index:1200;display:flex;flex-direction:column;padding:20px 14px 14px;background:color-mix(in srgb,var(--panel-solid,var(--panel,#09111d)) 94%,#02050a);border-right:1px solid color-mix(in srgb,var(--ui-accent,var(--accent,var(--gold,var(--neon,#63d9ff)))) 24%,transparent);box-shadow:12px 0 42px #0003;backdrop-filter:blur(22px);color:var(--text,#edf3ff);font:13px/1.4 Inter,system-ui,sans-serif;overflow-y:auto;scrollbar-width:thin}",
".f-contest-brand{display:flex;align-items:center;gap:12px;min-height:48px;padding:2px 9px 18px;border-bottom:1px solid #ffffff16;text-decoration:none;color:inherit}",
".f-contest-brand-mark{width:38px;height:38px;display:grid;place-items:center;flex:0 0 38px;border:1px solid var(--ui-accent,var(--accent,var(--gold,#69cfff)));border-radius:12px;color:var(--ui-accent,var(--accent,var(--gold,#69cfff)));background:color-mix(in srgb,var(--ui-accent,var(--accent,#69cfff)) 10%,transparent);font-size:20px;font-weight:900}",
".f-contest-brand strong{display:block;font-size:13px;letter-spacing:1.5px}.f-contest-brand small{display:block;margin-top:4px;color:var(--muted,#8fa0b8);font:9px ui-monospace,monospace;letter-spacing:1.3px}",
".f-contest-group{margin:22px 0 8px;padding-left:10px;color:var(--muted,#8392a8);font-size:10px;font-weight:750;letter-spacing:1.15px;text-transform:uppercase}",
".f-contest-link{position:relative;display:flex;align-items:center;gap:12px;min-height:42px;padding:9px 11px;border:1px solid transparent;border-radius:10px;color:var(--muted,#a5b0c2);text-decoration:none!important;font-size:12px;font-weight:600;transition:background .18s,border-color .18s,color .18s,transform .18s}",
".f-contest-link .f-contest-icon{display:grid;place-items:center;width:20px;flex:0 0 20px;color:var(--ui-accent,var(--accent,var(--gold,#69cfff)));font-size:15px}",
".f-contest-link:hover{color:var(--text,#fff);background:color-mix(in srgb,var(--ui-accent,var(--accent,#69cfff)) 9%,transparent);border-color:color-mix(in srgb,var(--ui-accent,var(--accent,#69cfff)) 18%,transparent);transform:translateX(2px)}.f-contest-link.is-active{color:var(--ui-accent,var(--accent,var(--gold,#69cfff)));background:color-mix(in srgb,var(--ui-accent,var(--accent,#69cfff)) 13%,transparent);border-color:color-mix(in srgb,var(--ui-accent,var(--accent,#69cfff)) 28%,transparent)}",
".f-contest-link.is-active:before{content:'';position:absolute;left:-1px;top:8px;bottom:8px;width:2px;border-radius:2px;background:var(--ui-accent,var(--accent,var(--gold,#69cfff)));box-shadow:0 0 12px var(--ui-accent,var(--accent,#69cfff))}",
".f-contest-foot{margin-top:auto;padding:15px 9px 5px;border-top:1px solid #ffffff16;color:var(--muted,#8fa0b8);font:9px/1.7 ui-monospace,monospace;letter-spacing:.6px}.f-contest-live{display:inline-block;width:7px;height:7px;margin-right:7px;border-radius:50%;background:var(--ui-accent,var(--accent,#69cfff));box-shadow:0 0 10px var(--ui-accent,var(--accent,#69cfff))}",
".f-contest-toggle{display:none}body.f-contest-has-sidebar{padding-left:258px!important}body.f-contest-has-sidebar .app{width:min(100% - 40px,900px)}",
"@media(max-width:900px){.f-contest-sidebar{width:250px;transform:translateX(-102%);transition:transform .24s ease}.f-contest-sidebar.is-open{transform:translateX(0)}body.f-contest-has-sidebar{padding-left:0!important}.f-contest-toggle{position:fixed;left:12px;top:12px;z-index:1201;display:grid;place-items:center;width:42px;height:42px;border:1px solid var(--ui-accent,var(--accent,#69cfff));border-radius:11px;background:var(--panel-solid,var(--panel,#101722));color:var(--text,#fff);font-size:19px;box-shadow:0 8px 25px #0006}body.f-contest-has-sidebar .app{padding-top:78px}}",
"@media(prefers-reduced-motion:reduce){.f-contest-sidebar,.f-contest-link{transition:none}}"
].join("");
const st=document.createElement("style");st.id="f-contest-sidebar-style";st.textContent=css;document.head.appendChild(st);
if(existing){
 const s=document.createElement("style");
 s.textContent=".sidebar{width:258px!important;padding:22px 14px!important;gap:0!important;backdrop-filter:blur(22px);box-shadow:12px 0 42px #0003}.sidebar .brand{padding:4px 9px 20px;border-bottom:1px solid #ffffff16}.sidebar .nav-label{margin:23px 0 9px 10px!important;font-size:10px!important;letter-spacing:1.15px!important;text-transform:uppercase}.sidebar .nav-item,.sidebar .nav a{min-height:42px;padding:9px 11px!important;margin:2px 0!important;border:1px solid transparent!important;border-radius:10px!important;font-size:12px!important;font-weight:600!important;transition:all .18s ease}.sidebar .nav-item:hover,.sidebar .nav a:hover{transform:translateX(2px)}.sidebar .nav-item.active,.sidebar .nav a.active{border-color:color-mix(in srgb,var(--accent,var(--gold,#69cfff)) 28%,transparent)!important}.sidebar-bottom,.side-foot{margin-top:auto!important;padding:15px 9px 5px;border-top:1px solid #ffffff16}";
 document.head.appendChild(s);return;
}
let links=[];
if(edu){
 const dash=document.querySelector("#dashboard");if(!dash)return;
 const els=[...dash.querySelectorAll(":scope > .section, :scope > .grid, :scope > .topline")];
 const icons=["⌂","◉","▦","✦","⌘","▤","♙"];
 els.forEach((el,i)=>{if(!el.id)el.id="edu-nav-"+i;const h=el.querySelector("h2,h3");links.push({href:"#"+el.id,label:h?.textContent?.trim()||["Bosh sahifa","Telegram","Modullar"][i]||"Bo‘lim",icon:icons[i%icons.length],group:i<3?"ASOSIY":"O‘RGANISH"})});
 if(document.querySelector("#moduleWorkspace"))links.push({href:"#moduleWorkspace",label:"Modul ish maydoni",icon:"⌘",group:"ISH MAYDONI"});
}else if(clim){
 links=[
 {href:"index.html",label:"Bosh sahifa",icon:"⌂",group:"PLATFORMA"},
 {href:"#platform",label:"Ekotizim modullari",icon:"▦",group:"PLATFORMA"},
 {href:"pages/monitoring.html",label:"Iqlim monitoringi",icon:"◉",group:"TAHLIL"},
 {href:"pages/map.html",label:"Ekologik xarita",icon:"◎",group:"TAHLIL"},
 {href:"pages/eco.html",label:"ECO RISK",icon:"⚑",group:"TAHLIL"},
 {href:"pages/ai.html",label:"Aqlli tahlil",icon:"⌘",group:"TAHLIL"},
 {href:"pages/carbon.html",label:"Uglerod izi",icon:"⌁",group:"TAHLIL"},
 {href:"pages/academy.html",label:"Ekologik ta’lim",icon:"▤",group:"JAMIYAT"},
 {href:"pages/action.html",label:"Ekologik harakat",icon:"✳",group:"JAMIYAT"},
 {href:"pages/insight.html",label:"Tadqiqotlar",icon:"⌕",group:"JAMIYAT"},
 {href:"pages/control.html",label:"Boshqaruv markazi",icon:"⬡",group:"PLATFORMA"}
 ];
}else if(nexus){
 const map=[["hero","Profilim","⌂","ASOSIY"],["nexus-stats","Ko‘rsatkichlar","◈","ASOSIY"],["nexus-rank","Kosmik maqom","♛","RIVOJLANISH"],["nexus-collect","Olmos yig‘ish","◇","RIVOJLANISH"],["nexus-world","NEXUS olami","◎","JAMIYAT"],["nexus-shop","Kosmik do‘kon","▣","JAMIYAT"],["nexus-inventory","Inventarim","▤","JAMIYAT"],["nexus-ranks","Darajalar xaritasi","⌁","RIVOJLANISH"]];
 const cards=[...document.querySelectorAll("main.app > section")];
 cards.forEach(el=>{const h=el.querySelector("h2")?.textContent?.trim();const x=map.find(v=>v[1]===h);if(x)el.id=x[0]});
 map.forEach(([id,label,icon,group])=>{if(document.getElementById(id))links.push({href:"#"+id,label,icon,group})});
}
if(!links.length)return;
const side=document.createElement("aside");side.className="f-contest-sidebar";side.setAttribute("aria-label","Asosiy navigatsiya");
const brand=document.createElement("a");brand.className="f-contest-brand";brand.href=edu?"#dashboard":clim?"index.html":"#hero";
brand.innerHTML='<span class="f-contest-brand-mark">'+(edu?"E":clim?"✳":"✦")+'</span><span><strong>'+(edu?"EDUCORE":clim?"CLIMORA":"NEXUS")+'</strong><small>'+(edu?"LEARN · EXPLORE · ACHIEVE":clim?"CLIMATE INTELLIGENCE":"COSMIC UNIVERSE")+'</small></span>';side.appendChild(brand);
let last="";
links.forEach(item=>{if(item.group!==last){const g=document.createElement("div");g.className="f-contest-group";g.textContent=item.group;side.appendChild(g);last=item.group}const a=document.createElement("a");a.className="f-contest-link";a.href=item.href;const ic=document.createElement("span");ic.className="f-contest-icon";ic.textContent=item.icon;const label=document.createElement("span");label.textContent=item.label;a.append(ic,label);a.addEventListener("click",()=>{side.querySelectorAll(".f-contest-link").forEach(x=>x.classList.remove("is-active"));a.classList.add("is-active");if(innerWidth<=900)side.classList.remove("is-open")});side.appendChild(a)});
const foot=document.createElement("div");foot.className="f-contest-foot";foot.innerHTML='<span class="f-contest-live"></span> TIZIM FAOL<br>ROBOCONTEST-INSPIRED UI';side.appendChild(foot);document.body.appendChild(side);document.body.classList.add("f-contest-has-sidebar");
const toggle=document.createElement("button");toggle.type="button";toggle.className="f-contest-toggle";toggle.setAttribute("aria-label","Yon panelni ochish");toggle.textContent="☰";toggle.addEventListener("click",()=>side.classList.toggle("is-open"));document.body.appendChild(toggle);
if(edu){const update=()=>{const visible=!document.querySelector("#dashboard")?.classList.contains("hidden");side.style.display=visible?"flex":"none";toggle.style.display=visible?"grid":"none"};update();new MutationObserver(update).observe(document.querySelector("#dashboard"),{attributes:true,attributeFilter:["class"]})}
if(nexus){const auth=document.querySelector("#authPanel");if(auth){const update=()=>{const visible=getComputedStyle(auth).display==="none";side.style.display=visible?"flex":"none";toggle.style.display=visible?"grid":"none"};new MutationObserver(update).observe(auth,{attributes:true,attributeFilter:["style","class"]});setTimeout(update,250)}}
})();

})();