import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CounterfactualPanel } from '@/components/findings/CounterfactualPanel';
import { mockCounterfactual } from '@/tests/mocks/data';

describe('CounterfactualPanel', () => {
  it('computable result shows before and after values', () => {
    render(<CounterfactualPanel result={mockCounterfactual} />);
    expect(screen.getByText(/EG-001 would not fire/)).toBeInTheDocument();
    expect(screen.getByText(/Required 0.19/)).toBeInTheDocument();
  });

  it('non-computable result shows the null reason', () => {
    render(
      <CounterfactualPanel
        result={{ ...mockCounterfactual, computable: false, plain_language: '', reason_if_null: 'Absence has no threshold.' }}
      />,
    );
    expect(screen.getByText(/Absence has no threshold/)).toBeInTheDocument();
  });

  it('a null result still renders the panel with an explanation', () => {
    render(<CounterfactualPanel result={null} />);
    expect(screen.getByText(/Counterfactual not available/)).toBeInTheDocument();
  });
});
