import { useState, useCallback } from 'react';
import { getProfileId, setProfileId } from '../services/api.js';

export function useProfileId() {
  const [profileId, setLocalProfileId] = useState(() => getProfileId());

  const updateProfileId = useCallback((id) => {
    setProfileId(id);
    setLocalProfileId(id);
  }, []);

  return [profileId, updateProfileId];
}
