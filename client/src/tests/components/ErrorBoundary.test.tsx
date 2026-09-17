import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ErrorBoundary } from '@/components/common/ErrorBoundary';

let shouldThrow = true;

function Exploding() {
  if (shouldThrow) {
    throw new Error('section exploded');
  }
  return <p>recovered content</p>;
}

describe('ErrorBoundary', () => {
  it('renders children when nothing throws', () => {
    render(
      <ErrorBoundary label="Calm section">
        <p>steady content</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText('steady content')).toBeInTheDocument();
  });

  it('catches a crash and offers a labelled reset', async () => {
    shouldThrow = true;
    const user = userEvent.setup();
    render(
      <ErrorBoundary label="Fragile section">
        <Exploding />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/Fragile section failed to render/)).toBeInTheDocument();
    shouldThrow = false;
    await user.click(screen.getByRole('button', { name: 'Retry request' }));
    expect(await screen.findByText('recovered content')).toBeInTheDocument();
  });
});
