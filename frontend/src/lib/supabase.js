import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://foxlhoexpadesglemozo.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZveGxob2V4cGFkZXNnbGVtb3pvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg4ODA3ODEsImV4cCI6MjEwNDQ1Njc4MX0.efRhGs-K2oN2_bMG5fgp3yFEyl5dUIaI62VxU6rFrXM';

export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
