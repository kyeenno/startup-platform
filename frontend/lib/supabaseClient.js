// Initiate Supabase connection 
import { createClient } from '@supabase/supabase-js';

// Supabase identifiers
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Creates client (gives access to authorisation)
export const supabase = createClient(supabaseUrl, supabaseAnonKey);