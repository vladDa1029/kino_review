import { useContext } from 'react';

import { ProjectContext } from './projectContextInstance';

export const useProjectContext = () => useContext(ProjectContext);
