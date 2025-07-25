/**
 * Supabase Configuration for Wildlife Graduate Assistantships Dashboard
 * 
 * IMPORTANT: Replace these values with your actual Supabase project credentials
 * The anon key is safe to expose in client-side code as it's protected by RLS policies
 */

// Replace these with your actual Supabase project values
const SUPABASE_CONFIG = {
    url: 'https://mqbkzveymkehgkbcjgba.supabase.co',
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xYmt6dmV5bWtlaGdrYmNqZ2JhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjM0MzYsImV4cCI6MjA2MzkzOTQzNn0.ojHZfb5ydVEVKQShv3pmW8bqXPksBc0jmJOfPz0lqCw'
};

// Initialize Supabase client (will be available globally)
let supabaseClient = null;

/**
 * Initialize Supabase client
 * This will be called when the Supabase library is loaded
 */
function initializeSupabase() {
    if (typeof supabase === 'undefined') {
        console.error('Supabase library not loaded');
        return false;
    }
    
    try {
        supabaseClient = supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);
        console.log('Supabase client initialized successfully');
        return true;
    } catch (error) {
        console.error('Failed to initialize Supabase client:', error);
        return false;
    }
}

/**
 * Check if Supabase is properly configured
 */
function isSupabaseConfigured() {
    return SUPABASE_CONFIG.url !== 'https://your-project-id.supabase.co' && 
           SUPABASE_CONFIG.anonKey !== 'your-anon-key-here';
}

// Configuration validation
if (!isSupabaseConfigured()) {
    console.warn('⚠️ Supabase not configured! Please update the values in supabase-config.js');
    console.warn('1. Replace SUPABASE_CONFIG.url with your project URL');
    console.warn('2. Replace SUPABASE_CONFIG.anonKey with your anon key');
    console.warn('3. Both can be found in your Supabase project settings > API');
}