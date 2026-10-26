import type { Experience, LearningGoal } from './lesson';
export const experienceOptions: {
  id: Experience;
  title: string;
  description: string;
}[] = [
  {
    id: 'beginner',
    title: 'Beginner',
    description: 'I’m learning how sketches, features and constraints work.',
  },
  {
    id: 'some-experience',
    title: 'Some experience',
    description: 'I can build simple parts and want help choosing operations.',
  },
  {
    id: 'comfortable',
    title: 'Comfortable',
    description: 'I know the basics and want to explore design reasoning.',
  },
];
export const goalOptions: { id: LearningGoal; title: string }[] = [
  { id: 'fundamentals', title: 'Learn CAD fundamentals' },
  { id: 'guided-project', title: 'Build a mounting bracket' },
  {
    id: 'design-reasoning',
    title: 'Follow a mounting plate from sketch to fillet',
  },
];
