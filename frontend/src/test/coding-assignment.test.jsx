import { beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ToastProvider } from '../components/ui';
import { api, allPages } from '../api/client';
import Workspace from '../pages/coding/Workspace';
import AssignmentEditor from '../pages/assignments/AssignmentEditor';

vi.mock('../api/client', () => ({api: {get: vi.fn(), post: vi.fn(), put: vi.fn()}, allPages: vi.fn(), errorText: () => 'Runner unavailable. Try again.'}));
vi.mock('../components/CodeEditor', () => ({default: ({value, onChange, readOnly}) => <textarea aria-label="Python code editor" value={value} readOnly={readOnly} onChange={e=>onChange(e.target.value)}/>}));

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  HTMLDialogElement.prototype.showModal = function(){this.open=true;};
});

function workspace() {
  api.get.mockImplementation(url => Promise.resolve({data: url.startsWith('/submissions/') ? {
    id: 7, assignment: 2, status: 'in_progress', attempt: 1, expires_at: new Date(Date.now()+600000).toISOString(),
    responses: [{question: 3, answer: ''}],
  } : {id: 2, title: 'Salary task', questions: [{id: 3, type: 'coding', title: 'Increase salaries', prompt: 'Add 10%.',
    difficulty: 'easy', marks: 10, starter_code: '# Write code', examples: [{input: 'Asha 20000', expected_output: 'Asha 22000.00'}]}]}}));
  render(<ToastProvider><MemoryRouter initialEntries={['/workspace/7']}><Routes>
    <Route path="/workspace/:id" element={<Workspace/>}/>
    <Route path="/submissions/:id" element={<p>Completed submission page</p>}/>
  </Routes></MemoryRouter></ToastProvider>);
}

it('lets the trainer insert, edit, and save salary input and expected output', async () => {
  allPages.mockImplementation(url => Promise.resolve(url==='/courses/'?[{id:1,title:'Python'}]:[]));
  api.post.mockResolvedValue({data:{id:2}});
  render(<ToastProvider><MemoryRouter initialEntries={['/assignments/new']}><Routes>
    <Route path="/assignments/new" element={<AssignmentEditor/>}/>
    <Route path="/assignments/:id" element={<p>Draft preview</p>}/>
  </Routes></MemoryRouter></ToastProvider>);
  fireEvent.click(await screen.findByRole('button',{name:'Use salary increment example'}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm',exact:true}));
  await waitFor(()=>expect(screen.getByLabelText('Input data (stdin)').value).toContain('Asha 20000'));
  expect(screen.getByLabelText('Expected output').value).toBe('Asha 22000.00\nRavi 33000.00\nMeena 27500.00');
  fireEvent.change(screen.getByLabelText('Course'),{target:{value:'1'}});
  fireEvent.change(screen.getByLabelText('Input data (stdin)'),{target:{value:'1\nAsha 20000'}});
  fireEvent.change(screen.getByLabelText('Expected output'),{target:{value:'Asha 22000.00'}});
  fireEvent.click(screen.getByRole('button',{name:'Save draft & preview'}));
  await screen.findByText('Draft preview');
  expect(api.post.mock.calls[0][1].questions[0].test_cases).toEqual([{input:'1\nAsha 20000',expected_output:'Asha 22000.00',is_hidden:false,weight:1}]);
});

it('keeps mismatches editable and completes only after a successful server check', async () => {
  api.post.mockResolvedValueOnce({data:{completed:false,results:[{accepted:false,status:'Wrong Answer',stdout:'Asha 20000',expected_output:'Asha 22000.00'}]}})
    .mockResolvedValueOnce({data:{completed:true,submission:{id:7},results:[]}});
  workspace();
  const editor=await screen.findByLabelText('Python code editor');
  fireEvent.change(editor,{target:{value:'print("Asha 20000")'}});
  fireEvent.click(screen.getByRole('button',{name:'Check & complete'}));
  await screen.findByText(/Task not complete yet/);
  expect(screen.getByText('Your output')).toBeTruthy();
  expect(editor.readOnly).toBe(false);
  fireEvent.change(editor,{target:{value:'print("Asha 22000.00")'}});
  expect(screen.queryByText('Wrong Answer')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Check & complete'}));
  await screen.findByText('Completed submission page');
  expect(api.post).toHaveBeenLastCalledWith('/submissions/7/check-complete/',{answers:{3:'print("Asha 22000.00")'}});
  expect(sessionStorage.getItem('sf-answers-7')).toBeNull();
});

it('prevents duplicate completion and preserves the draft if the runner fails', async () => {
  let reject;
  api.post.mockImplementation(()=>new Promise((resolve,fail)=>{reject=fail;}));
  workspace();
  const editor=await screen.findByLabelText('Python code editor');
  fireEvent.change(editor,{target:{value:'print(1)'}});
  const check=screen.getByRole('button',{name:'Check & complete'});
  fireEvent.click(check);
  expect(check.disabled).toBe(true);
  expect(editor.readOnly).toBe(true);
  fireEvent.click(check);
  expect(api.post).toHaveBeenCalledTimes(1);
  reject(new Error('Runner unavailable'));
  await screen.findByText('Runner unavailable. Try again.');
  expect(editor.readOnly).toBe(false);
  expect(JSON.parse(sessionStorage.getItem('sf-answers-7'))['3']).toBe('print(1)');
});

it('distinguishes custom execution from expected-output checks', async () => {
  api.post.mockResolvedValue({data:{results:[{accepted:true,status:'Accepted',stdout:'anything'}]}});
  workspace();
  await screen.findByLabelText('Python code editor');
  fireEvent.click(screen.getByRole('button',{name:'Run custom input'}));
  await screen.findByText('Executed');
  expect(screen.getByText('Custom input runs do not check the expected output or complete the task.')).toBeTruthy();
  expect(api.post.mock.calls[0][0]).toBe('/code/run/');
  expect(screen.getByRole('button',{name:'Check & complete'}).disabled).toBe(false);
});
