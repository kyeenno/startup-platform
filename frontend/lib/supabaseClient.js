// Initiate Supabase connection 
import { createClient } from '@supabase/supabase-js';

// Supabase identifiers
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Creates client (gives access to authorisation) + configure sessions and auto refresh
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: false,
        storageKey: 'supabase-auth',
        storage: typeof window !== 'undefined' ? window.localStorage : undefined
    }
});