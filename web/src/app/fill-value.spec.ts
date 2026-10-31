import { describe, expect, it } from 'vitest';

import { fillValue, problemMessage } from './fill-value';

describe('fillValue', () => {
  it('takes the first number for numeric properties', () => {
    expect(fillValue('250/300 Bar', 'number')).toBe('250');
    expect(fillValue('230 Bar', 'number')).toBe('230');
    expect(fillValue('~108 lpm', 'number')).toBe('108');
    expect(fillValue('2.5 mm', 'number')).toBe('2.5');
  });

  it('keeps non-numeric numeric-property values as printed', () => {
    expect(fillValue('NA', 'number')).toBe('NA');
  });

  it('keeps text values as printed', () => {
    expect(fillValue('Mineral ISO VG68', 'text')).toBe('Mineral ISO VG68');
  });
});

describe('problemMessage', () => {
  it('reads the detail of a problem response', () => {
    expect(problemMessage({ response: '{"detail":"\'abc\' is not a number"}' })).toBe("'abc' is not a number");
  });

  it('falls back to the error message', () => {
    expect(problemMessage(new Error('boom'))).toBe('boom');
  });
});
