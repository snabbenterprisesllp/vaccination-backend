# Flutter OTP Authentication - Implementation Guide

## Setup

### 1. Add Dependencies to `pubspec.yaml`

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  shared_preferences: ^2.2.2
  provider: ^6.1.1
```

## Implementation

### 1. Create API Service (`lib/services/auth_api_service.dart`)

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthApiService {
  static const String baseUrl = 'http://localhost:8000/api/v1/auth';
  
  /// Send OTP to mobile number
  Future<Map<String, dynamic>> sendOTP(String mobileNumber) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/send-otp'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'mobile_number': mobileNumber}),
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to send OTP');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
  
  /// Verify OTP
  Future<Map<String, dynamic>> verifyOTP(
    String mobileNumber,
    String otp,
    String? deviceInfo,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/verify-otp'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'mobile_number': mobileNumber,
          'otp': otp,
          'device_info': deviceInfo,
        }),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        // Save tokens if provided
        if (data['access_token'] != null) {
          await _saveTokens(
            data['access_token'],
            data['refresh_token'],
          );
        }
        
        return data;
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Invalid OTP');
      }
    } catch (e) {
      throw Exception('Verification failed: $e');
    }
  }
  
  /// Complete registration for new users
  Future<Map<String, dynamic>> completeRegistration({
    required String mobileNumber,
    required String fullName,
    required String role,
    String? email,
    String? hospitalId,
    bool consentGiven = true,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/complete-registration'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'mobile_number': mobileNumber,
          'full_name': fullName,
          'role': role,
          'email': email,
          'hospital_id': hospitalId,
          'consent_given': consentGiven,
        }),
      );
      
      if (response.statusCode == 201) {
        final data = json.decode(response.body);
        
        // Save tokens
        await _saveTokens(
          data['access_token'],
          data['refresh_token'],
        );
        
        return data;
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Registration failed');
      }
    } catch (e) {
      throw Exception('Registration error: $e');
    }
  }
  
  /// Get current user info
  Future<Map<String, dynamic>> getCurrentUser() async {
    final token = await _getAccessToken();
    
    if (token == null) {
      throw Exception('Not authenticated');
    }
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/me'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else if (response.statusCode == 401) {
        // Try to refresh token
        final refreshed = await _refreshToken();
        if (refreshed) {
          return getCurrentUser(); // Retry
        }
        throw Exception('Session expired');
      } else {
        throw Exception('Failed to get user info');
      }
    } catch (e) {
      throw Exception('Error: $e');
    }
  }
  
  /// Refresh access token
  Future<bool> _refreshToken() async {
    final refreshToken = await _getRefreshToken();
    
    if (refreshToken == null) return false;
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/refresh-token'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'refresh_token': refreshToken}),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        await _saveAccessToken(data['access_token']);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
  
  /// Logout
  Future<void> logout() async {
    final token = await _getAccessToken();
    
    if (token != null) {
      try {
        await http.post(
          Uri.parse('$baseUrl/logout'),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
        );
      } catch (e) {
        // Ignore errors
      }
    }
    
    await _clearTokens();
  }
  
  // Token storage helpers
  Future<void> _saveTokens(String accessToken, String refreshToken) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', accessToken);
    await prefs.setString('refresh_token', refreshToken);
  }
  
  Future<void> _saveAccessToken(String accessToken) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', accessToken);
  }
  
  Future<String?> _getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  Future<String?> _getRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('refresh_token');
  }
  
  Future<void> _clearTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
  }
}
```

### 2. Create Login Screen (`lib/screens/login_screen.dart`)

```dart
import 'package:flutter/material.dart';
import '../services/auth_api_service.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _authService = AuthApiService();
  final _mobileController = TextEditingController();
  final _otpController = TextEditingController();
  
  bool _isLoading = false;
  bool _otpSent = false;
  String? _errorMessage;
  String? _maskedMobile;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Login')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: _otpSent ? _buildOTPVerification() : _buildMobileInput(),
      ),
    );
  }
  
  Widget _buildMobileInput() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          'Enter Mobile Number',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        SizedBox(height: 24),
        TextField(
          controller: _mobileController,
          keyboardType: TextInputType.phone,
          decoration: InputDecoration(
            labelText: 'Mobile Number',
            hintText: '+919876543210',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.phone),
          ),
        ),
        SizedBox(height: 16),
        if (_errorMessage != null)
          Text(
            _errorMessage!,
            style: TextStyle(color: Colors.red),
          ),
        SizedBox(height: 16),
        ElevatedButton(
          onPressed: _isLoading ? null : _sendOTP,
          child: _isLoading
              ? CircularProgressIndicator(color: Colors.white)
              : Text('Send OTP'),
          style: ElevatedButton.styleFrom(
            minimumSize: Size(double.infinity, 50),
          ),
        ),
      ],
    );
  }
  
  Widget _buildOTPVerification() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          'Enter OTP',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        SizedBox(height: 8),
        Text('Sent to $_maskedMobile'),
        SizedBox(height: 24),
        TextField(
          controller: _otpController,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: InputDecoration(
            labelText: 'OTP',
            hintText: '123456',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.lock),
          ),
        ),
        SizedBox(height: 16),
        if (_errorMessage != null)
          Text(
            _errorMessage!,
            style: TextStyle(color: Colors.red),
          ),
        SizedBox(height: 16),
        ElevatedButton(
          onPressed: _isLoading ? null : _verifyOTP,
          child: _isLoading
              ? CircularProgressIndicator(color: Colors.white)
              : Text('Verify OTP'),
          style: ElevatedButton.styleFrom(
            minimumSize: Size(double.infinity, 50),
          ),
        ),
        SizedBox(height: 16),
        TextButton(
          onPressed: () {
            setState(() {
              _otpSent = false;
              _errorMessage = null;
              _otpController.clear();
            });
          },
          child: Text('Change Number'),
        ),
      ],
    );
  }
  
  Future<void> _sendOTP() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      final result = await _authService.sendOTP(_mobileController.text);
      setState(() {
        _otpSent = true;
        _maskedMobile = result['mobile_number'];
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }
  
  Future<void> _verifyOTP() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      final result = await _authService.verifyOTP(
        _mobileController.text,
        _otpController.text,
        'Flutter Android App', // Device info
      );
      
      if (result['is_new_user']) {
        // Navigate to registration screen
        Navigator.pushReplacementNamed(
          context,
          '/register',
          arguments: _mobileController.text,
        );
      } else {
        // Navigate to home screen
        Navigator.pushReplacementNamed(context, '/home');
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }
}
```

### 3. Create Registration Screen (`lib/screens/registration_screen.dart`)

```dart
import 'package:flutter/material.dart';
import '../services/auth_api_service.dart';

class RegistrationScreen extends StatefulWidget {
  final String mobileNumber;
  
  RegistrationScreen({required this.mobileNumber});
  
  @override
  _RegistrationScreenState createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends State<RegistrationScreen> {
  final _authService = AuthApiService();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  
  bool _isLoading = false;
  String _selectedRole = 'parent';
  String? _errorMessage;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Complete Registration')),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _nameController,
              decoration: InputDecoration(
                labelText: 'Full Name *',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),
            TextField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(
                labelText: 'Email (Optional)',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _selectedRole,
              decoration: InputDecoration(
                labelText: 'I am a',
                border: OutlineInputBorder(),
              ),
              items: [
                DropdownMenuItem(value: 'parent', child: Text('Parent')),
                DropdownMenuItem(value: 'hospital', child: Text('Hospital')),
              ],
              onChanged: (value) {
                setState(() {
                  _selectedRole = value!;
                });
              },
            ),
            SizedBox(height: 24),
            if (_errorMessage != null)
              Text(
                _errorMessage!,
                style: TextStyle(color: Colors.red),
              ),
            SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _completeRegistration,
              child: _isLoading
                  ? CircularProgressIndicator(color: Colors.white)
                  : Text('Complete Registration'),
              style: ElevatedButton.styleFrom(
                minimumSize: Size(double.infinity, 50),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Future<void> _completeRegistration() async {
    if (_nameController.text.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter your name';
      });
      return;
    }
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      await _authService.completeRegistration(
        mobileNumber: widget.mobileNumber,
        fullName: _nameController.text,
        role: _selectedRole,
        email: _emailController.text.isEmpty ? null : _emailController.text,
      );
      
      Navigator.pushReplacementNamed(context, '/home');
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }
}
```

## Usage

1. Add routes to your app
2. Use `AuthApiService` for all auth operations
3. Tokens are automatically stored in SharedPreferences
4. Access tokens are automatically refreshed when expired


