import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const credentialPath=path.resolve('../.task-temp/browser-credentials.json');

test('login is usable on desktop and mobile',async({page})=>{
  await page.goto('/login');
  await expect(page.getByRole('heading',{name:'Welcome back.',exact:true})).toBeVisible();
  await expect(page.getByLabel('Email address')).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('button',{name:'Sign in to workspace'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('trainer routes render without browser exceptions',async({page})=>{
  test.skip(!fs.existsSync(credentialPath),'Run scripts/prepare-e2e.py and start the isolated API first.');
  const credentials=JSON.parse(fs.readFileSync(credentialPath,'utf8'));
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/login');
  await page.getByLabel('Email address').fill(credentials.trainer);
  await page.getByLabel('Password',{exact:true}).fill(credentials.password);
  await page.getByRole('button',{name:'Sign in to workspace'}).click();
  await expect(page.getByRole('heading',{name:'Welcome back, Alex.'})).toBeVisible();
  for(const route of ['students','courses','topics','materials','generator','assignments','submissions','performance','reports','leaderboard','notifications','settings','profile']){
    await page.goto(`/${route}`);
    await expect(page.locator('main h1')).toBeVisible();
  }
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Welcome back, Alex.'})).toBeVisible();
  await page.getByRole('button',{name:'Open navigation'}).click();
  await expect(page.getByRole('link',{name:'Courses',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});
