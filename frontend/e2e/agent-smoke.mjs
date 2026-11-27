// Own-app integration checks against the actual local TLS runtime. Real configured assistant, synthetic/empty dossier.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash, X509Certificate } from 'node:crypto';
import { mkdtemp, readFile, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const temp=await mkdtemp(path.join(os.tmpdir(),'ledgerflow-agent-ui-'));
const output=path.join(repo,'artifacts/agent-runtime');
await mkdir(output,{recursive:true});
const statusFile=path.join(temp,'ready.json');
const processHandle=spawn(path.join(repo,'.venv/bin/python'),[path.join(repo,'native/desktop/server.py'),'--data-dir',path.join(temp,'data'),'--status-file',statusFile],{cwd:repo,stdio:['ignore','ignore','pipe']});
let diagnostics=''; processHandle.stderr.on('data',chunk=>{diagnostics=(diagnostics+chunk.toString()).slice(-12000);});
const errors=[]; const checks=[];
const check=name=>{checks.push(name); console.log(`PASS ${name}`);};
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let browser;
let page;
try {
  let status;
  for(let i=0;i<150;i++) {
    try { status=JSON.parse(await readFile(statusFile,'utf8')); break; } catch {}
    if(processHandle.exitCode!==null) throw new Error('Local runtime exited before ready');
    await wait(200);
  }
  assert(status,'Local runtime did not become ready');
  const cert=await readFile(path.join(temp,'data/tls-cert.pem'));
  const spki=new X509Certificate(cert).publicKey.export({type:'spki',format:'der'});
  const certificateKey=createHash('sha256').update(spki).digest('base64');
  browser=await chromium.launch({channel:'chrome',headless:true,args:[`--ignore-certificate-errors-spki-list=${certificateKey}`]});
  const context=await browser.newContext({viewport:{width:1512,height:982}});
  await context.addInitScript(()=>{if(!localStorage.getItem('ledgerflow.appearance'))localStorage.setItem('ledgerflow.appearance','light');});
  page=await context.newPage();
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`${status.origin}/#/bootstrap/${encodeURIComponent(status.bootstrap)}`);
  await page.getByRole('heading',{name:'Votre agent comptable',exact:true}).waitFor();
  await page.getByText('Vision connectée',{exact:true}).waitFor();
  assert(!page.url().includes(status.bootstrap));
  assert.equal(await page.getByLabel('Invite code').count(),0);
  assert.equal(await page.getByLabel('Workspace address').count(),0);
  check('Actual Mac bootstrap opens the agent with no server-address or invite form; one-use token is removed from history');
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:false,animations:'disabled'});
  await page.getByRole('button',{name:'Explique-moi comment ça fonctionne',exact:true}).click();
  await page.locator('.agent-message.assistant').waitFor({timeout:150000});
  assert((await page.locator('.agent-message.assistant p').innerText()).length>40);
  assert(await page.getByRole('button',{name:'Envoyer le message',exact:true}).isVisible());
  check('Live configured language model responds in the actual app; composer remains available');
  await page.screenshot({path:path.join(output,'desktop-conversation.png'),fullPage:false,animations:'disabled'});
  await page.getByRole('button',{name:'Scan with iPhone',exact:true}).click();
  await page.getByRole('button',{name:'Afficher le code d’association',exact:true}).click();
  await page.locator('.local-phone .pairing-qr').waitFor();
  assert(await page.getByLabel('Retrouver tout mon espace',{exact:false}).isChecked());
  await page.getByRole('button',{name:'Fermer',exact:true}).click();
  check('Mac phone association generates a real one-use QR and can revoke it by closing');
  const htmlOverflow=()=>document.documentElement.scrollWidth>innerWidth;
  assert.equal(await page.evaluate(htmlOverflow),false);
  await page.setViewportSize({width:1280,height:800});
  assert.equal(await page.evaluate(htmlOverflow),false);
  await page.screenshot({path:path.join(output,'desktop-1280.png'),fullPage:false,animations:'disabled'});
  check('Desktop 1512 and 1280 layouts have no page horizontal overflow');
  await page.setViewportSize({width:393,height:852});
  await page.locator('.mobile-finance-tabs').waitFor({state:'visible'});
  assert.equal(await page.getByRole('button',{name:'Scan with iPhone',exact:true}).isVisible(),false);
  assert(await page.locator('.phone-direct-capture').isVisible());
  assert.equal(await page.evaluate(htmlOverflow),false);
  const send=await page.getByRole('button',{name:'Envoyer le message',exact:true}).boundingBox();
  assert(send && send.y+send.height<780,'Composer must remain above phone navigation');
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:false,animations:'disabled'});
  await page.getByRole('navigation',{name:'Navigation iPhone'}).getByRole('link',{name:'Scanner',exact:true}).click();
  await page.getByText('No workbook is ready yet.',{exact:true}).waitFor();
  await page.screenshot({path:path.join(output,'mobile-capture-empty.png'),fullPage:false});
  check('Full phone workspace has Agent/Dossiers/Scanner/Settings navigation and an honest missing-workbook capture state');
  await page.getByRole('navigation',{name:'Navigation iPhone'}).getByRole('link',{name:'Réglages',exact:true}).click();
  await page.getByRole('heading',{name:'Connexion du modèle',exact:true}).waitFor();
  assert.equal(await page.getByText('Install LedgerFlow',{exact:false}).count(),0);
  await page.screenshot({path:path.join(output,'mobile-settings.png'),fullPage:false,animations:'disabled'});
  check('Phone settings describe the actual local application and expose model-status/configuration recovery');
  await page.getByRole('navigation',{name:'Navigation iPhone'}).getByRole('link',{name:'Agent',exact:true}).click();
  await page.setViewportSize({width:1512,height:982});
  await page.evaluate(()=>{localStorage.setItem('ledgerflow.appearance','dark');});
  await page.reload();
  await page.getByRole('heading',{name:'Votre agent comptable',exact:true}).waitFor();
  await page.locator('.agent-message.assistant').waitFor();
  assert.equal(await page.evaluate(()=>document.documentElement.dataset.appearance),'dark');
  assert.notEqual(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(247, 247, 243)');
  await page.screenshot({path:path.join(output,'desktop-dark.png'),fullPage:false,animations:'disabled'});
  assert.equal(await page.evaluate(htmlOverflow),false);
  check('Dark appearance preserves the live conversation after reload');
  assert.deepEqual(errors,[]);
  await writeFile(path.join(output,'browser-verification.json'),JSON.stringify({checks,uncaughtErrors:errors,scope:'Own-app browser integration; phone viewport emulation, not physical camera or native iOS validation'},null,2)+'\n');
} catch(error) {
  if(diagnostics) await writeFile(path.join(output,'ui-failure.log'),diagnostics);
  if(page) {
    await page.screenshot({path:path.join(output,'ui-failure.png'),fullPage:false}).catch(()=>undefined);
    await writeFile(path.join(output,'ui-failure.json'),JSON.stringify({errors,text:(await page.locator('body').innerText().catch(()=>'' )).slice(0,10000)},null,2));
  }
  throw error;
} finally {
  await browser?.close();
  processHandle.kill('SIGTERM');
  await new Promise(resolve=>{if(processHandle.exitCode!==null) resolve(); else {processHandle.once('exit',resolve);setTimeout(()=>{processHandle.kill('SIGKILL');resolve();},10000).unref();}});
  await rm(temp,{recursive:true,force:true});
}
