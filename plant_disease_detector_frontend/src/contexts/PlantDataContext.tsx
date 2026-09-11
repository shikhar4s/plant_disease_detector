import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import type { Analysis } from '../lib/types';

interface PlantDataContextType {
  selectedImage: Analysis | null;
  setSelectedImage: (image: Analysis | null) => void;
}
const PlantDataContext = createContext<PlantDataContextType | undefined>(undefined);

export function usePlantData() {
  const context = useContext(PlantDataContext);
  if (!context) throw new Error('usePlantData must be used within PlantDataProvider');
  return context;
}

export function PlantDataProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [selectedImage, setSelectedImage] = useState<Analysis | null>(null);
  useEffect(() => { setSelectedImage(null); }, [user?.id]);
  return <PlantDataContext.Provider value={{ selectedImage, setSelectedImage }}>{children}</PlantDataContext.Provider>;
}
