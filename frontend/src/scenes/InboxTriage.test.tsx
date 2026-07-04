import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import InboxTriage from '@/scenes/InboxTriage';
import type { InboxTriagePayload } from '@/types';

const payload: InboxTriagePayload = {
  role: 'Engineer',
  instruction: 'Pick 2 of these 3 candidates.',
  select_count: 2,
  timer_seconds: null,
  candidates: [
    {
      id: 'a',
      name: 'Alex Anderson',
      headline: 'Engineer',
      years_experience: 5,
      education: 'BSc',
      skills: ['Python'],
      highlights: ['Did a thing'],
    },
    {
      id: 'b',
      name: 'Brooke Bennett',
      headline: 'Engineer',
      years_experience: 5,
      education: 'BSc',
      skills: ['Python'],
      highlights: ['Did a thing'],
    },
    {
      id: 'c',
      name: 'Casey Carter',
      headline: 'Engineer',
      years_experience: 5,
      education: 'BSc',
      skills: ['Python'],
      highlights: ['Did a thing'],
    },
  ],
};

describe('InboxTriage', () => {
  it('disables Continue until the required number of candidates are picked', () => {
    render(<InboxTriage payload={payload} onSubmit={vi.fn()} />);
    const submit = screen.getByRole('button', { name: /continue/i });
    expect(submit).toBeDisabled();

    fireEvent.click(screen.getByText('Alex Anderson'));
    expect(submit).toBeDisabled();

    fireEvent.click(screen.getByText('Brooke Bennett'));
    expect(submit).toBeEnabled();
  });

  it('submits with the selected IDs and an elapsed time', () => {
    const onSubmit = vi.fn();
    render(<InboxTriage payload={payload} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByText('Alex Anderson'));
    fireEvent.click(screen.getByText('Casey Carter'));
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const [choice, elapsedMs] = onSubmit.mock.calls[0];
    expect(choice).toEqual({ selected_ids: ['a', 'c'] });
    expect(typeof elapsedMs).toBe('number');
    expect(elapsedMs).toBeGreaterThanOrEqual(0);
  });

  it('caps selection at select_count', () => {
    render(<InboxTriage payload={payload} onSubmit={vi.fn()} />);
    const alex = screen.getByText('Alex Anderson').closest('button')!;
    const brooke = screen.getByText('Brooke Bennett').closest('button')!;
    const casey = screen.getByText('Casey Carter').closest('button')!;
    fireEvent.click(alex);
    fireEvent.click(brooke);
    fireEvent.click(casey);
    // Third click should be ignored because select_count = 2.
    expect(alex.getAttribute('aria-pressed')).toBe('true');
    expect(brooke.getAttribute('aria-pressed')).toBe('true');
    expect(casey.getAttribute('aria-pressed')).toBe('false');
  });
});
