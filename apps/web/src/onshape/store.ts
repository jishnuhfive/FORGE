import { createContext, useContext } from 'react';
import { standaloneState } from './model';
export const OnshapeContext = createContext(standaloneState);
export const useOnshapeContext = () => useContext(OnshapeContext);
