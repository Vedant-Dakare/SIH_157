import { afterEach, describe, expect, it, vi } from 'vitest';

import { server } from '@/tests/mocks/handlers';
import { errorHandlers } from '@/tests/mocks/handlers';

describe('lib/api', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('throws at module load for an external VITE_API_URL', async () => {
    vi.stubEnv('VITE_API_URL', 'http://evil.example.com:8080');
    vi.resetModules();
    await expect(import('@/lib/api')).rejects.toThrow(/non-loopback/i);
  });

  it('getEntities returns typed data matching the Zod schema', async () => {
    const { getEntities } = await import('@/lib/api');
    const body = await getEntities('demo');
    expect(body.run_id).toBe('demo');
    expect(body.entities).toHaveLength(5);
    expect(body.entities[0]?.band).toBe('HIGH');
  });

  it('wraps API errors in a typed ApiError', async () => {
    server.use(errorHandlers[0]);
    const module = await import('@/lib/api');
    try {
      await module.getEntities('demo');
      expect.unreachable('expected ApiError');
    } catch (error) {
      expect(error).toBeInstanceOf(module.ApiError);
      expect((error as InstanceType<typeof module.ApiError>).status).toBe(500);
    }
  });

  it('wraps Zod parse failures in a typed ApiError', async () => {
    server.use(errorHandlers[1]);
    const module = await import('@/lib/api');
    try {
      await module.getFinding('f-eg1');
      expect.unreachable('expected ApiError');
    } catch (error) {
      expect(error).toBeInstanceOf(module.ApiError);
      expect((error as InstanceType<typeof module.ApiError>).status).toBeNull();
    }
  });
});
