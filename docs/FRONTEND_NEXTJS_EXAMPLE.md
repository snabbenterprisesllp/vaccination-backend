# Next.js OTP Authentication - Implementation Guide

## Setup

### 1. Install Dependencies

```bash
npm install axios js-cookie
npm install --save-dev @types/js-cookie
```

## Implementation

### 1. Create API Service (`src/services/authService.ts`)

```typescript
import axios from 'axios';
import Cookies from 'js-cookie';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface SendOTPResponse {
  success: boolean;
  message: string;
  mobile_number: string;
  expires_in_seconds: number;
}

export interface VerifyOTPResponse {
  success: boolean;
  message: string;
  is_new_user: boolean;
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
}

export interface UserResponse {
  id: number;
  mobile_number: string;
  email?: string;
  full_name?: string;
  role: string;
  hospital_id?: string;
  is_active: boolean;
  created_at: string;
}

class AuthService {
  private api = axios.create({
    baseURL: `${API_BASE_URL}/auth`,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  /**
   * Send OTP to mobile number
   */
  async sendOTP(mobileNumber: string): Promise<SendOTPResponse> {
    const { data } = await this.api.post<SendOTPResponse>('/send-otp', {
      mobile_number: mobileNumber,
    });
    return data;
  }

  /**
   * Verify OTP
   */
  async verifyOTP(
    mobileNumber: string,
    otp: string,
    deviceInfo?: string
  ): Promise<VerifyOTPResponse> {
    const { data } = await this.api.post<VerifyOTPResponse>('/verify-otp', {
      mobile_number: mobileNumber,
      otp,
      device_info: deviceInfo,
    });

    // Save tokens if provided
    if (data.access_token && data.refresh_token) {
      this.saveTokens(data.access_token, data.refresh_token);
    }

    return data;
  }

  /**
   * Complete registration for new users
   */
  async completeRegistration(params: {
    mobile_number: string;
    full_name: string;
    role: 'parent' | 'hospital';
    email?: string;
    hospital_id?: string;
    consent_given?: boolean;
  }): Promise<VerifyOTPResponse> {
    const { data } = await this.api.post<VerifyOTPResponse>(
      '/complete-registration',
      params
    );

    // Save tokens
    if (data.access_token && data.refresh_token) {
      this.saveTokens(data.access_token, data.refresh_token);
    }

    return data;
  }

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<UserResponse> {
    const token = this.getAccessToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const { data } = await this.api.get<UserResponse>('/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return data;
    } catch (error: any) {
      if (error.response?.status === 401) {
        // Try to refresh token
        const refreshed = await this.refreshToken();
        if (refreshed) {
          return this.getCurrentUser(); // Retry
        }
      }
      throw error;
    }
  }

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const { data } = await this.api.post('/refresh-token', {
        refresh_token: refreshToken,
      });

      this.saveAccessToken(data.access_token);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  /**
   * Logout
   */
  async logout(): Promise<void> {
    const token = this.getAccessToken();

    if (token) {
      try {
        await this.api.post('/logout', null, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch {
        // Ignore errors
      }
    }

    this.clearTokens();
  }

  /**
   * Token management
   */
  private saveTokens(accessToken: string, refreshToken: string) {
    // Save tokens in HTTP-only cookies (more secure)
    Cookies.set('access_token', accessToken, {
      expires: 1 / 96, // 15 minutes
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
    });
    Cookies.set('refresh_token', refreshToken, {
      expires: 7, // 7 days
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
    });
  }

  private saveAccessToken(accessToken: string) {
    Cookies.set('access_token', accessToken, {
      expires: 1 / 96, // 15 minutes
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
    });
  }

  getAccessToken(): string | undefined {
    return Cookies.get('access_token');
  }

  private getRefreshToken(): string | undefined {
    return Cookies.get('refresh_token');
  }

  private clearTokens() {
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
}

export default new AuthService();
```

### 2. Create Login Page (`src/app/login/page.tsx`)

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import authService from '@/services/authService';

export default function LoginPage() {
  const router = useRouter();
  const [mobileNumber, setMobileNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [maskedMobile, setMaskedMobile] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const result = await authService.sendOTP(mobileNumber);
      setOtpSent(true);
      setMaskedMobile(result.mobile_number);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const result = await authService.verifyOTP(
        mobileNumber,
        otp,
        navigator.userAgent
      );

      if (result.is_new_user) {
        // Redirect to registration
        router.push(`/register?mobile=${encodeURIComponent(mobileNumber)}`);
      } else {
        // Redirect to dashboard
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid OTP');
    } finally {
      setIsLoading(false);
    }
  };

  if (!otpSent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
          <div>
            <h2 className="text-center text-3xl font-bold text-gray-900">
              Login
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Enter your mobile number to receive OTP
            </p>
          </div>

          <form onSubmit={handleSendOTP} className="mt-8 space-y-6">
            <div>
              <label htmlFor="mobile" className="sr-only">
                Mobile Number
              </label>
              <input
                id="mobile"
                name="mobile"
                type="tel"
                required
                className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="+919876543210"
                value={mobileNumber}
                onChange={(e) => setMobileNumber(e.target.value)}
              />
            </div>

            {error && (
              <div className="text-red-600 text-sm text-center">{error}</div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? 'Sending...' : 'Send OTP'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-center text-3xl font-bold text-gray-900">
            Enter OTP
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sent to {maskedMobile}
          </p>
        </div>

        <form onSubmit={handleVerifyOTP} className="mt-8 space-y-6">
          <div>
            <label htmlFor="otp" className="sr-only">
              OTP
            </label>
            <input
              id="otp"
              name="otp"
              type="text"
              required
              maxLength={6}
              className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm text-center text-2xl tracking-widest"
              placeholder="123456"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm text-center">{error}</div>
          )}

          <button
            type="submit"
            disabled={isLoading || otp.length !== 6}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {isLoading ? 'Verifying...' : 'Verify OTP'}
          </button>

          <button
            type="button"
            onClick={() => {
              setOtpSent(false);
              setOtp('');
              setError('');
            }}
            className="w-full text-center text-sm text-indigo-600 hover:text-indigo-500"
          >
            Change Number
          </button>
        </form>
      </div>
    </div>
  );
}
```

### 3. Create Registration Page (`src/app/register/page.tsx`)

```typescript
'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import authService from '@/services/authService';

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const mobileNumber = searchParams.get('mobile') || '';

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'parent' | 'hospital'>('parent');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await authService.completeRegistration({
        mobile_number: mobileNumber,
        full_name: fullName,
        role,
        email: email || undefined,
        consent_given: true,
      });

      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-center text-3xl font-bold text-gray-900">
            Complete Registration
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div>
            <input
              type="text"
              required
              className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Full Name *"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <div>
            <input
              type="email"
              className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Email (Optional)"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <select
              className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={role}
              onChange={(e) => setRole(e.target.value as 'parent' | 'hospital')}
            >
              <option value="parent">I am a Parent</option>
              <option value="hospital">I am a Hospital</option>
            </select>
          </div>

          {error && (
            <div className="text-red-600 text-sm text-center">{error}</div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {isLoading ? 'Registering...' : 'Complete Registration'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

### 4. Create Auth Context (`src/contexts/AuthContext.tsx`)

```typescript
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import authService, { UserResponse } from '@/services/authService';

interface AuthContextType {
  user: UserResponse | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    if (authService.isAuthenticated()) {
      try {
        const userData = await authService.getCurrentUser();
        setUser(userData);
      } catch {
        setUser(null);
      }
    }
    setIsLoading(false);
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
    router.push('/login');
  };

  const refreshUser = async () => {
    await loadUser();
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

## Environment Variables

Add to `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Usage

1. Wrap your app with `AuthProvider`
2. Use `authService` for all auth operations
3. Use `useAuth()` hook to access auth state
4. Tokens are stored in HTTP-only cookies for security


