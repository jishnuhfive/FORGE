import { isLesson } from './lesson';
import type { Lesson } from './lesson';
import { sketchToSolid } from './sample';

export type LessonResource =
  | { status: 'ready'; lesson: Lesson }
  | { status: 'empty' | 'unavailable' | 'load-error' | 'invalid' };

// Local synchronous catalog. No network/provider fallback or synthetic checking.
export function loadLesson(
  id: string | null,
  source: () => unknown = () => sketchToSolid,
): LessonResource {
  if (id === null) return { status: 'empty' };
  if (id !== 'sketch-to-solid') return { status: 'unavailable' };
  try {
    const value = source();
    return isLesson(value) && value.id === id
      ? { status: 'ready', lesson: value }
      : { status: 'invalid' };
  } catch {
    return { status: 'load-error' };
  }
}
export const sampleResource = loadLesson('sketch-to-solid');
