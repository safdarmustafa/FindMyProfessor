import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../lib/supabase.js';

const PROFILE_KEY = 'fmp_profile_id';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession()
      .then(({ data }) => {
        if (!mounted) return;
        setUser(data?.session?.user || null);
        setLoading(false);
      })
      .catch(() => { if (mounted) setLoading(false); });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!mounted) return;
      setUser(session?.user || null);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const signOut = useCallback(async () => {
    try { await supabase.auth.signOut(); } catch {}
    try { localStorage.removeItem(PROFILE_KEY); } catch {}
    setUser(null);
  }, []);

  return { user, loading, signOut };
}
