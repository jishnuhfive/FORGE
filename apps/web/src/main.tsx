import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { GlassDefinitions } from '@forge/design-system';
import { App } from './App';
import './styles.css';

const root = document.getElementById('root');
if (!root) throw new Error('Missing application root');

createRoot(root).render(
  <StrictMode>
    <GlassDefinitions />
    <App />
  </StrictMode>,
);
