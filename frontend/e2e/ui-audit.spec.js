import { test, expect } from '@playwright/test';
import fs from 'node:fs';

async function visit(page, route) {
  if (page.url() === 'about:blank' || route === '/login') await page.goto(route);
  else await page.evaluate(path => { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }, route);
  await page.waitForLoadState('networkidle');
}
const credentials=JSON.parse(fs.readFileSync('../.task-temp/browser-credentials.json','utf8'));

test('dashboard actions filter work, empty searches recover, and mobile navigation traps focus',async({page})=>{
  await visit(page,'/login');
  await page.getByLabel('Email address',{exact:true}).fill(credentials.trainer);
  await page.getByRole('button',{name:'Open my workspace'}).click();
  await expect(page.getByRole('heading',{name:'What would you like to do next?'})).toBeVisible();
  await page.getByRole('link',{name:/Review submissions/}).click();
  await expect(page.getByRole('combobox',{name:'Submission status'})).toHaveValue('submitted');
  await page.reload();
  await expect(page.getByRole('combobox',{name:'Submission status'})).toHaveValue('submitted');
  await visit(page,'/assignments');
  await page.getByRole('textbox',{name:'Search assignments'}).fill('no-assignment-has-this-title-ux-check');
  await expect(page.getByRole('heading',{name:'No matching assignments'})).toBeVisible();
  await page.locator('.empty').getByRole('button',{name:'Clear filters'}).click();
  await expect(page.getByRole('textbox',{name:'Search assignments'})).toHaveValue('');
  await expect(page.getByRole('heading',{name:'No matching assignments'})).toHaveCount(0);
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Open navigation'}).click();
  const drawer=page.getByRole('dialog',{name:'Workspace navigation'});
  const close=drawer.getByRole('button',{name:'Close navigation'});
  await expect(close).toBeFocused();
  expect(await page.locator('.main-shell').evaluate(element=>element.inert)).toBe(true);
  await page.keyboard.press('Shift+Tab');
  await expect(drawer.getByRole('button',{name:'Sign out'})).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(close).toBeFocused();
  expect(await page.evaluate(()=>document.body.style.overflow)).toBe('hidden');
  await close.click();
  await expect(page.getByRole('button',{name:'Open navigation'})).toBeFocused();
  expect(await page.evaluate(()=>document.body.style.overflow)).not.toBe('hidden');
});
const routes={admin:['/','/team','/students','/courses','/topics','/batches','/assignments','/submissions','/performance','/notifications','/profile'],sales:['/','/team','/students','/courses','/batches','/assignments','/submissions','/performance','/notifications','/profile'],trainer:['/','/batches','/students','/courses','/topics','/materials','/generator','/assignments','/assignments/new','/submissions','/performance','/reports','/leaderboard','/notifications','/settings','/profile'],student:['/','/assignments','/coding','/submissions','/performance','/reports','/learning-path','/leaderboard','/notifications','/profile']};
async function audit(page,route){
  await expect(page.locator('main h1')).toHaveCount(1);
  await expect(page.locator('main [role="alert"]')).toHaveCount(0);
  const issues=await page.evaluate(()=>{
    const visible=e=>!!(e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden');
    const name=e=>e.getAttribute('aria-label')||e.getAttribute('aria-labelledby')||e.textContent.trim();
    const problems=[];
    for(const e of document.querySelectorAll('button,a'))if(visible(e)&&!name(e))problems.push(`Unnamed ${e.tagName}: ${e.outerHTML.slice(0,140)}`);
    for(const e of document.querySelectorAll('input:not([type=hidden]),select,textarea'))if(visible(e)&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby')&&!e.labels?.length)problems.push(`Unlabeled ${e.tagName}: ${e.outerHTML.slice(0,120)}`);
    for(const e of document.querySelectorAll('label'))if(visible(e)&&!e.control)problems.push(`Unassociated label: ${e.textContent.slice(0,70)}`);
    if(document.documentElement.scrollWidth>window.innerWidth+1)problems.push(`Horizontal overflow ${document.documentElement.scrollWidth}/${window.innerWidth}`);
    if(document.querySelector('a a,button button,button a,a button,label label'))problems.push('Nested interactive element');
    for(const e of document.querySelectorAll('.badge'))if(!e.dataset.tone||!e.textContent.trim()||/undefined|null/.test(e.textContent))problems.push('Invalid badge');
    for(const e of document.querySelectorAll('.badge'))if(visible(e)&&e.getBoundingClientRect().height>40)problems.push('Status tag wraps into multiple lines');
    return problems;
  });
  expect(issues,route).toEqual([]);
}
for(const role of Object.keys(routes))test(`${role}: every page, control label, status tag, mobile and dark theme`,async({page})=>{
  test.setTimeout(180000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await visit(page,'/login');await page.getByRole('textbox',{name:'Email address',exact:true}).fill(credentials[role]);await page.getByRole('button',{name:'Open my workspace'}).click();await expect(page.locator('main h1')).toBeVisible();
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:1000});
    for(const route of routes[role]){await visit(page,route);await expect(page.locator('main h1')).toBeVisible();await audit(page,`${role} ${width} ${route}`);}
  }
  await visit(page,'/');await page.getByRole('button',{name:'Toggle color theme'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');await audit(page,`${role} dark`);
  await page.screenshot({path:`../artifacts/ui-${role}-mobile-dark.png`,fullPage:true});
  await page.getByRole('button',{name:'Toggle color theme'}).click();await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:`../artifacts/ui-${role}-desktop.png`,fullPage:true});expect(errors).toEqual([]);
});

test('dialogs expose titles and keyboard dismissal; mobile menu supports Escape',async({page})=>{
  await visit(page,'/login');await page.getByRole('textbox',{name:'Email address',exact:true}).fill(credentials.trainer);await page.getByRole('button',{name:'Open my workspace'}).click();await expect(page.locator('main h1')).toBeVisible();
  for(const [route,button,title] of [['/students','Add student','Grant student access'],['/courses','New course','New course'],['/batches','Create batch','Create batch'],['/materials','Add material','Add study material']]){
    await visit(page,route);const trigger=page.getByRole('button',{name:button,exact:true});await trigger.click();await expect(page.getByRole('dialog',{name:title,exact:true})).toBeVisible();await audit(page,route+' dialog');await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(trigger).toBeFocused();
  }
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Open navigation'}).click();await expect(page.getByRole('dialog',{name:'Workspace navigation'}).getByRole('button',{name:'Close navigation'})).toHaveAttribute('aria-expanded','true');await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Open navigation'})).toBeFocused();
});

test('assignment, editor, submission, report and student workspace details',async({page})=>{
  test.setTimeout(90000);
  test.skip(!fs.existsSync('../.task-temp/ui-details.json'),'Run scripts/prepare-e2e.py to create isolated detail-page fixtures.');
  const data=JSON.parse(fs.readFileSync('../.task-temp/ui-details.json','utf8'));
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(const role of ['trainer','student']){
    if(role==='student'){await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'Sign out',exact:true}).click();}
    await visit(page,'/login');await page.getByRole('textbox',{name:'Email address',exact:true}).fill(credentials[role]);await page.getByRole('button',{name:'Open my workspace'}).click();await expect(page.locator('main h1')).toBeVisible();
    const paths=[`/assignments/${data.assignment}`,`/submissions/${data.submission}`,`/reports/${data.report}`];
    if(role==='trainer')paths.push(`/assignments/${data.draft}/edit`,`/students/${data.student}`);
    for(const width of [1440,390]){await page.setViewportSize({width,height:1000});for(const path of paths){await visit(page,path);await expect(page.locator('main h1')).toBeVisible();await audit(page,`${role} ${width} ${path}`);}}
    if(role==='student'){
      await visit(page,`/assignments/${data.assignment}`);await page.getByRole('button',{name:/Start assessment|Continue attempt/}).click();await expect(page.getByRole('textbox',{name:'Your answer'})).toBeVisible();await audit(page,'student answer workspace');
      await page.getByRole('textbox',{name:'Your answer'}).fill('4');await page.getByRole('button',{name:'Submit assessment',exact:true}).click();await expect(page.getByRole('dialog',{name:'Submit your assessment?'})).toBeVisible();await page.getByRole('dialog').getByRole('button',{name:'Submit assessment',exact:true}).click();await expect(page.getByText('Results awaiting trainer release',{exact:true})).toBeVisible();
      await visit(page,`/submissions/${data.submission}`);await expect(page.getByRole('heading',{name:'Output did not match'})).toBeVisible();await page.screenshot({path:'../artifacts/ui-output-comparison-mobile.png',fullPage:true});
    }
  }
  expect(errors).toEqual([]);
});
