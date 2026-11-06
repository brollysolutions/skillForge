import { test, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within, configure } from '@testing-library/react';
import App from '../App';
import { appPath } from '../utils/paths';

// Opt-in only: targets the isolated database created by the documented E2E fixture.
// No mocks replace HTTP requests. Provider calls are covered by backend contract tests.
test.skipIf(!process.env.SKILLFORGE_E2E)('trainer-to-student assessment lifecycle through the rendered UI and live API',async()=>{
  configure({asyncUtilTimeout:15000});
  const credentials=JSON.parse(process.env.SF_E2E_CREDENTIALS);
  const suffix=Date.now().toString();
  const course=`Python Foundations ${suffix}`;
  const title=`Function check ${suffix}`;
  const studentEmail=`learner-${suffix}@browser.test`;
  window.history.replaceState({},'', appPath('login'));
  HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  global.ResizeObserver=class { observe(){} unobserve(){} disconnect(){} };
  render(<App/>);
  async function click(name){fireEvent.click(await screen.findByRole('button',{name,exact:true}));}
  async function fill(label,value){fireEvent.change(await screen.findByLabelText(label,{exact:true}),{target:{value}});}
  async function login(email){await fill('Email address',email);await click('Open my workspace');await screen.findByRole('heading',{name:/Welcome back,/},{timeout:15000});}
  await login(credentials.trainer);
  fireEvent.click(screen.getByRole('link',{name:'Students',exact:true}));
  await click('Add student');await fill('Student name',`Learner ${suffix}`);await fill('Personal email',studentEmail);await click('Grant access');
  await screen.findByText('Access granted. The student can now sign in with their email.',{exact:true});
  fireEvent.click(screen.getByRole('link',{name:'Courses',exact:true}));
  await click('New course');await fill('Title',course);await fill('Description','Python course created by the integration test.');await click('Save course');
  await screen.findByRole('heading',{name:course});
  fireEvent.click(screen.getByRole('link',{name:'Study materials',exact:true}));
  await click('Add material');await click('Write notes');await fill('Material title',`Functions ${suffix}`);
  const courseSelect=screen.getByLabelText('Course',{exact:true});
  await waitFor(()=>expect([...courseSelect.options].some(o=>o.text===course)).toBe(true));
  const courseId=[...courseSelect.options].find(o=>o.text===course).value;
  fireEvent.change(courseSelect,{target:{value:courseId}});
  await fill('Class notes','Python functions use def and return values to their callers.');
  await click('Save material');await screen.findByText(`Functions ${suffix}`,{exact:true});
  fireEvent.click(screen.getByRole('link',{name:'Assignments',exact:true}));
  fireEvent.click(await screen.findByRole('link',{name:'Manual assignment',exact:true}));
  await fill('Assignment title',title);await fill('Course',courseId);await fill('Question type','mcq');await fill('Title','Function keyword');await fill('Problem statement','Which keyword defines a Python function?');
  await fill('Options (one per line)','def\nclass');await fill('Correct answers (one option per line)','def');
  await click('Save draft & preview');await screen.findByRole('heading',{name:title});
  await click('Approve & publish');await click('Confirm');await click('Assign students');
  const dialog=await screen.findByRole('dialog');
  fireEvent.click(await within(dialog).findByRole('checkbox',{name:new RegExp(studentEmail.replaceAll('.','\\.'))}));
  await click('Assign selected');await screen.findByText('Assessment assigned.',{exact:true});
  await click('Sign out');await login(studentEmail);
  fireEvent.click(screen.getByRole('link',{name:'My assignments',exact:true}));
  fireEvent.click(await screen.findByRole('link',{name:title,exact:true}));
  await click('Start assessment');
  fireEvent.click(await screen.findByRole('radio',{name:'def',exact:true}));
  await click('Save answers');
  await screen.findByText(/Saved at /);
  await click('Submit assessment');
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Submit assessment',exact:true}));
  await screen.findByText('Results awaiting trainer release',{exact:true});
  expect(screen.getByText('Pending',{exact:true})).toBeTruthy();
  await click('Sign out');await login(credentials.trainer);
  fireEvent.click(screen.getByRole('link',{name:'Assignments',exact:true}));
  fireEvent.click(await screen.findByRole('link',{name:title,exact:true}));
  await click('Close assessment');await click('Confirm');
  await screen.findByText('Assignment closed.',{exact:true});
  await screen.findByText('Closed',{exact:true});
  await click('Release results');await click('Confirm');await screen.findByText('Results released.',{exact:true});
  await click('Sign out');await login(studentEmail);
  fireEvent.click(screen.getByRole('link',{name:'My submissions',exact:true}));
  const assignmentCell=await screen.findByText(title,{exact:true});
  fireEvent.click(within(assignmentCell.closest('tr')).getByRole('link',{name:'Review',exact:true}));
  expect((await screen.findAllByText('10 / 10',{exact:true})).length).toBe(2);
  expect(screen.getByText('100%',{exact:true})).toBeTruthy();
  fireEvent.click(screen.getByRole('link',{name:'Profile',exact:true}));
  expect(await screen.findByRole('heading',{name:'My profile'})).toBeTruthy();
  expect(screen.queryByLabelText('Current password')).toBeNull();
},120000);
