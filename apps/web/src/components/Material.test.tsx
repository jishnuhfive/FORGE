import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { GlassSurface } from '@forge/design-system';

describe('event-driven glass', () => {
  it('queues at most one frame, reads layout only on entry and cancels on leave', () => {
    const raf = vi.fn().mockReturnValue(7);
    const cancel = vi.fn();
    vi.stubGlobal('requestAnimationFrame', raf);
    vi.stubGlobal('cancelAnimationFrame', cancel);
    render(<GlassSurface>Material</GlassSurface>);
    const material = screen.getByText('Material');
    const bounds = vi
      .spyOn(material, 'getBoundingClientRect')
      .mockReturnValue({ left: 0, top: 0, width: 300, height: 100 } as DOMRect);
    expect(raf).not.toHaveBeenCalled();
    fireEvent.pointerEnter(material);
    for (let i = 0; i < 20; i++)
      fireEvent.pointerMove(material, { clientX: i, clientY: i });
    expect(raf).toHaveBeenCalledOnce();
    expect(bounds).toHaveBeenCalledOnce();
    fireEvent.pointerLeave(material);
    expect(cancel).toHaveBeenCalledWith(7);
    fireEvent.pointerMove(material);
    expect(raf).toHaveBeenCalledOnce();
  });
  it('does not track with an opaque accessibility material', () => {
    const raf = vi.fn();
    vi.stubGlobal('requestAnimationFrame', raf);
    render(
      <div data-transparency="reduced">
        <GlassSurface>Opaque material</GlassSurface>
      </div>,
    );
    const material = screen.getByText('Opaque material');
    fireEvent.pointerEnter(material);
    fireEvent.pointerMove(material);
    expect(raf).not.toHaveBeenCalled();
  });
  it('cancels pending work when hidden or unmounted', () => {
    const raf = vi.fn().mockReturnValue(9);
    const cancel = vi.fn();
    vi.stubGlobal('requestAnimationFrame', raf);
    vi.stubGlobal('cancelAnimationFrame', cancel);
    const view = render(<GlassSurface>Material</GlassSurface>);
    const material = screen.getByText('Material');
    vi.spyOn(material, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      top: 0,
      width: 300,
      height: 100,
    } as DOMRect);
    fireEvent.pointerEnter(material);
    fireEvent.pointerMove(material);
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
    fireEvent(document, new Event('visibilitychange'));
    expect(cancel).toHaveBeenCalledWith(9);
    view.unmount();
  });
});
