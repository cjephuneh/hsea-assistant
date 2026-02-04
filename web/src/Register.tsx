import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from './api';
import type { User } from './api';
import { useAuth } from './AuthContext';

export function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    
    // Validate required fields
    if (!name.trim()) {
      setError('Name is required');
      return;
    }
    if (!email.trim()) {
      setError('Email is required');
      return;
    }
    if (!password || password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const { data, status } = await api.auth.register(
        name.trim(),
        email.trim(),
        password,
        phone.trim() || undefined
      );
      
      if (status === 201 && data && 'access_token' in data) {
        localStorage.setItem('access_token', (data as { access_token: string }).access_token);
        // Reload page to trigger AuthContext to fetch user
        window.location.href = '/dashboard';
        return;
      }
      
      // Show backend error message if available
      const errorMsg = (data as { error?: string })?.error;
      setError(errorMsg || 'Registration failed. Please try again.');
    } catch (err) {
      console.error('Registration error:', err);
      setError('Registration failed. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-icon">✨</div>
        <h1>Create account</h1>
        <p className="auth-subtitle">Get started with HSEA Assistant</p>
        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="text"
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <input
            type="tel"
            placeholder="Phone (optional)"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>
        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
