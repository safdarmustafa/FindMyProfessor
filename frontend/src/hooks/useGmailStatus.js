import { useState, useEffect, useCallback } from 'react';
import { getGmailStatus } from '../services/gmail.js';

export function useGmailStatus() {
  const [status, setStatus] = useState(null); // { connected, email }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getGmailStatus();
      setStatus(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refetch(); }, [refetch]);

  return { status, loading, error, refetch };
}
