import { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';

/**
 * Hook to prevent API calls when user is not authenticated.
 * Automatically redirects to login if session becomes invalid.
 */
export function useApiGuard() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const hasRedirected = useRef(false);

  useEffect(() => {
    // Don't redirect if already on login/register page
    if (location.pathname === '/login' || location.pathname === '/register') {
      return;
    }
    // Check if we have a token even if user isn't loaded yet
    const hasToken = !!localStorage.getItem('access_token');
    
    if (!loading && !user && !hasToken && !hasRedirected.current) {
      hasRedirected.current = true;
      navigate('/login', { replace: true });
    }
  }, [user, loading, navigate, location.pathname]);

  // Allow requests if we have a token OR if user is loaded
  // This prevents blocking requests right after login before AuthContext finishes loading
  const hasToken = !!localStorage.getItem('access_token');
  const canMakeRequests = hasToken || (!loading && !!user);

  return { user, loading, canMakeRequests };
}
