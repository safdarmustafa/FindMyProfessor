import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../lib/supabase.js';
import { clearProfileId } from '../services/api.js';

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

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      // Signed out anywhere (another tab, expired session): the stored
      // profile id belongs to that old session, so drop it.
      if (event === 'SIGNED_OUT') clearProfileId();
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
    clearProfileId();
    setUser(null);
  }, []);

  return { user, loading, signOut };
}
