'use client';

import { createContext, useContext } from 'react';

// Context for processing tasks - allows MainApp to register its addProcessingTask function
type ProcessingContextType = {
  registerProcessingHandler: (handler: (taskId: string, url: string) => void) => void;
  unregisterProcessingHandler: () => void;
};

export const ProcessingContext = createContext<ProcessingContextType>({
  registerProcessingHandler: () => {},
  unregisterProcessingHandler: () => {},
});

export const useProcessing = () => useContext(ProcessingContext);
