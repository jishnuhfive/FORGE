import { isLesson } from './lesson';
import type { Lesson } from './lesson';
import { mountingBracket } from './bracket';
import { sketchToSolid } from './sample';

export type LessonResource =
  | { status: 'ready'; lesson: Lesson }
  | { status: 'empty' | 'unavailable' | 'load-error' | 'invalid' };

// Local synchronous catalog. No network/provider fallback or synthetic checking.
export function loadLesson(
  id: string | null,
  source: (id: string) => unknown = (id) =>
    id === 'mounting-bracket' ? mountingBracket : sketchToSolid,
): LessonResource {
  if (id === null) return { status: 'empty' };
  if (id !== 'sketch-to-solid' && id !== 'mounting-bracket')
    return { status: 'unavailable' };
  try {
    const value = source(id);
    return isLesson(value) && value.id === id
      ? { status: 'ready', lesson: value }
      : { status: 'invalid' };
  } catch {
    return { status: 'load-error' };
  }
}
export const sampleResource = loadLesson('sketch-to-solid');
export const bracketResource = loadLesson('mounting-bracket');
