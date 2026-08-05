import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://whymvwuzjaffltkjkfoj.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndoeW12d3V6amFmZmx0a2prZm9qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUzOTU4ODgsImV4cCI6MjEwMDk3MTg4OH0.Cfqfgi-1uGQlj3S2_2yI8uaNYNGTDOYawD8do7qnohI'   // ← Dán anon key của bạn vào đây

export const supabase = createClient(supabaseUrl, supabaseKey)