import { test, expect } from '@playwright/test';
import fs from 'node:fs';

async function visit(page, route) {
  if (page.url() === 'about:blank' || route === '/login') await page.goto(route);
  else await page.evaluate(path => { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }, route);
  await page.waitForLoadState('networkidle');
}
import path from 'node:path';
const credentialPath=path.resolve('../.task-temp/browser-credentials.json');

test('login is usable on desktop and mobile',async({page})=>{
  await visit(page,'/login');
  await expect(page.getByRole('heading',{name:'Welcome back.',exact:true})).toBeVisible();
  await expect(page.getByLabel('Email address')).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('button',{name:'Open my workspace'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('trainer routes render without browser exceptions',async({page})=>{
  test.skip(!fs.existsSync(credentialPath),'Run scripts/prepare-e2e.py and start the isolated API first.');
  const credentials=JSON.parse(fs.readFileSync(credentialPath,'utf8'));
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await visit(page,'/login');
  await page.getByLabel('Email address').fill(credentials.trainer);
  await page.getByRole('button',{name:'Open my workspace'}).click();
  await expect(page.getByRole('heading',{name:'Welcome back, Alex.'})).toBeVisible({timeout:15000});
  for(const route of ['batches','students','courses','topics','materials','generator','assignments','submissions','performance','reports','leaderboard','notifications','settings','profile']){
    await visit(page,`/${route}`);
    await expect(page.locator('main h1')).toBeVisible();
  }
  await page.setViewportSize({width:390,height:844});
  await visit(page,'/');
  await expect(page.getByRole('heading',{name:'Welcome back, Alex.'})).toBeVisible();
  await page.getByRole('button',{name:'Open navigation'}).click();
  await expect(page.getByRole('link',{name:'Courses',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});

test('sales enrolls a batch and trainer publishes its task',async({page})=>{
  test.skip(!fs.existsSync(credentialPath),'Prepare the isolated API fixture first.');
  const c=JSON.parse(fs.readFileSync(credentialPath,'utf8')), suffix=Date.now(), title=`Course ${suffix}`, batch=`Batch ${suffix}`, task=`Task ${suffix}`;
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const login=async email=>{await visit(page,'/login');await page.getByLabel('Email address').fill(email);await page.getByRole('button',{name:'Open my workspace'}).click();await expect(page.locator('main h1')).toBeVisible();};
  await login(c.sales);
  await visit(page,'/team');await expect(page.getByRole('heading',{name:'Trainers',exact:true})).toBeVisible();
  await visit(page,'/courses');await page.getByRole('button',{name:'New course'}).click();await page.getByLabel('Title',{exact:true}).fill(title);await page.getByRole('combobox',{name:'Course trainer',exact:true}).selectOption({label:`Alex Morgan (${c.trainer})`});await page.getByRole('button',{name:'Save course',exact:true}).click();await expect(page.getByRole('heading',{name:title})).toBeVisible();
  await visit(page,'/batches');await page.getByRole('button',{name:'Create batch',exact:true}).click();await page.getByLabel('Batch name').fill(batch);await page.getByRole('combobox',{name:'Course',exact:true}).selectOption({label:title});await page.getByRole('combobox',{name:'Trainer',exact:true}).selectOption({label:`Alex Morgan (${c.trainer})`});await page.getByRole('dialog').getByRole('button',{name:'Create batch',exact:true}).click();
  const card=page.locator('.course-card').filter({has:page.getByRole('heading',{name:batch,exact:true})});await card.getByRole('button',{name:'Enroll students'}).click();await page.getByRole('dialog').getByRole('checkbox',{name:new RegExp(c.student.replaceAll('.','\\.'))}).check();await page.getByRole('button',{name:'Enroll selected',exact:true}).click();await expect(card).toContainText('1 student');await page.screenshot({path:'../artifacts/sales-batches-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await login(c.trainer);await visit(page,'/batches');await card.getByRole('link',{name:'Create / upload task'}).click();await page.getByLabel('Assignment title').fill(task);await page.getByLabel('Title',{exact:true}).fill('Double the input');await page.getByLabel('Problem statement').fill('Read an integer and print twice its value.');await page.getByLabel('Deadline',{exact:true}).fill('2027-12-01T12:00');await page.getByLabel('Input',{exact:true}).fill('3');await page.getByLabel('Expected output',{exact:true}).fill('6');await expect(page.getByRole('button',{name:'Add test case'})).toBeDisabled();await page.getByRole('button',{name:'Save draft & preview'}).click();await expect(page.getByRole('heading',{name:task,exact:true})).toBeVisible();await page.getByRole('button',{name:'Approve & publish'}).click();await page.getByRole('button',{name:'Confirm',exact:true}).click();await expect(page.getByRole('button',{name:'Assign students',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Manage student access',exact:true}).click();await expect(page.getByRole('dialog',{name:'Student access',exact:true})).toContainText(c.student);await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await login(c.student);await visit(page,'/assignments');await expect(page.getByRole('link',{name:task,exact:true})).toBeVisible();await page.setViewportSize({width:390,height:844});await visit(page,'/');await expect(page.locator('main h1')).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);await page.screenshot({path:'../artifacts/student-dashboard-mobile.png',fullPage:true});expect(errors).toEqual([]);
});

test('admin sees team and organization results',async({page})=>{
  test.skip(!fs.existsSync(credentialPath),'Prepare the isolated API fixture first.');
  const c=JSON.parse(fs.readFileSync(credentialPath,'utf8'));
  await visit(page,'/login');await page.getByLabel('Email address').fill(c.admin);await page.getByRole('button',{name:'Open my workspace'}).click();await expect(page.locator('main h1')).toBeVisible();await page.screenshot({path:'../artifacts/admin-dashboard-desktop.png',fullPage:true});
  for(const route of ['team','students','courses','batches','performance','submissions']){await visit(page,`/${route}`);await expect(page.locator('main h1')).toBeVisible();}
});

test('sales grants, revokes and restores student email access; sessions survive reload',async({page})=>{
  test.setTimeout(90000);
  const c=JSON.parse(fs.readFileSync(credentialPath,'utf8'));
  const email=`access-${Date.now()}@browser.test`;
  const login=async value=>{
    await visit(page,'/login');
    await page.getByLabel('Email address').fill(value);
    await page.getByRole('button',{name:'Open my workspace'}).click();
  };
  await login(c.sales);
  await expect(page.locator('main h1')).toBeVisible();
  await visit(page,'/students');
  await page.getByRole('button',{name:'Add student',exact:true}).click();
  await page.getByLabel('Student name',{exact:true}).fill('Access Lifecycle');
  await page.getByLabel('Personal email',{exact:true}).fill(email);
  await page.getByRole('button',{name:'Grant access',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await login(email.toUpperCase());
  await expect(page.locator('main h1')).toBeVisible();
  await page.reload();
  await expect(page.locator('main h1')).toBeVisible();
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await login(c.sales);
  await expect(page.locator('main h1')).toBeVisible();
  await visit(page,'/students');
  await page.getByRole('textbox',{name:'Search students',exact:true}).fill(email);
  const row=page.getByRole('row').filter({hasText:email});
  await row.getByRole('button',{name:'Deactivate',exact:true}).click();
  await expect(row.getByRole('button',{name:'Reactivate',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await login(email);
  await expect(page.getByRole('alert')).toContainText('does not have active access');
  await expect(page).toHaveURL(/\/login$/);
  await login(c.sales);
  await expect(page.locator('main h1')).toBeVisible();
  await visit(page,'/students');
  await page.getByRole('textbox',{name:'Search students',exact:true}).fill(email);
  await row.getByRole('button',{name:'Reactivate',exact:true}).click();
  await expect(row.getByRole('button',{name:'Deactivate',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await login(email);
  await expect(page.locator('main h1')).toBeVisible();
});
