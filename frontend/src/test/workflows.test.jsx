import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ActionButton, ToastProvider, Pagination } from '../components/ui';
import { errorText } from '../api/client';

describe('Assessment UI controls',()=>{
  it('prevents duplicate actions while a request is pending',async()=>{
    let finish;const action=vi.fn(()=>new Promise(resolve=>{finish=resolve;}));
    render(<ToastProvider><ActionButton action={action} success="Saved">Submit</ActionButton></ToastProvider>);
    fireEvent.click(screen.getByRole('button',{name:'Submit'}));
    expect(screen.getByRole('button',{name:'Submit'}).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button',{name:'Submit'}));expect(action).toHaveBeenCalledTimes(1);
    finish({});await waitFor(()=>expect(screen.getByRole('button',{name:'Submit'}).disabled).toBe(false));
    expect(screen.getByRole('status').textContent).toContain('Saved');
  });
  it('shows actionable backend errors',async()=>{
    render(<ToastProvider><ActionButton action={()=>Promise.reject({response:{data:{detail:'The deadline has passed.'}}})}>Submit</ActionButton></ToastProvider>);
    fireEvent.click(screen.getByRole('button',{name:'Submit'}));
    await waitFor(()=>expect(screen.getByRole('status').textContent).toContain('The deadline has passed.'));
  });
  it('only enables valid pagination directions',()=>{
    render(<Pagination data={{count:30,previous:null,next:'page2'}} page={1} setPage={()=>{}}/>);
    expect(screen.getByRole('button',{name:/Previous/}).disabled).toBe(true);
    expect(screen.getByRole('button',{name:/Next/}).disabled).toBe(false);
  });
  it('formats validation errors without exposing raw HTML',()=>{
    expect(errorText({response:{data:{email:['Enter a valid email.']}}})).toContain('Enter a valid email.');
    expect(errorText({response:{data:'<html>internal failure</html>'}})).not.toContain('<html>');
  });
});
