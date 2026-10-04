import { createContext, useContext } from 'react';
import type { Me } from './api';

export const AuthContext = createContext<{
  me: Me;
  reload: () => Promise<void>;
  endSession: (expired?: boolean) => void;
} | null>(null);

export const useAuth = () => useContext(AuthContext);
