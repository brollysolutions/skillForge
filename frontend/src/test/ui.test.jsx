import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Field, Button, Badge } from '../components/ui';

describe('Accessible shared controls',()=>{
  it('labels dropdowns independently of their options and connects validation feedback',()=>{
    render(<Field label="Course" hint="Choose a course you teach." error="Choose a course."><select required><option>Python foundations</option></select></Field>);
    const select=screen.getByRole('combobox',{name:'Course',exact:true});
    expect(select.getAttribute('aria-invalid')).toBe('true');
    const descriptions=select.getAttribute('aria-describedby').split(' ').map(id=>document.getElementById(id).textContent);
    expect(descriptions).toEqual(['Choose a course you teach.','Choose a course.']);
  });
  it('ordinary action buttons do not accidentally submit surrounding forms',()=>{
    const submit=vi.fn(e=>e.preventDefault());render(<form onSubmit={submit}><Button>Add a question</Button><Button type="submit">Save draft</Button></form>);
    fireEvent.click(screen.getByRole('button',{name:'Add a question'}));expect(submit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Save draft'}));expect(submit).toHaveBeenCalledTimes(1);
  });
  it('status tags have readable labels and distinct success/failure states',()=>{
    render(<><Badge>pending_review</Badge><Badge>Accepted</Badge><Badge>Wrong Answer</Badge><Badge>{null}</Badge></>);
    expect(screen.getByText('Needs review').dataset.tone).toBe('caution');
    expect(screen.getByText('Accepted').dataset.tone).toBe('positive');
    expect(screen.getByText('Wrong Answer').dataset.tone).toBe('negative');
    expect(screen.getByText('Not set').dataset.tone).toBe('neutral');
  });
});
