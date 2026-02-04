import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_service.dart';
import '../models/user.dart';

class AuthService extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  
  User? _user;
  bool _isAuthenticated = false;

  User? get user => _user;
  bool get isAuthenticated => _isAuthenticated;

  AuthService() {
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    final token = await _storage.read(key: 'access_token');
    if (token != null) {
      try {
        final response = await _apiService.get('/auth/me');
        if (response.statusCode == 200) {
          _user = User.fromJson(response.data);
          _isAuthenticated = true;
          notifyListeners();
        }
      } catch (e) {
        await _storage.delete(key: 'access_token');
      }
    }
  }

  Future<bool> login(String email, String password) async {
    try {
      print('🔐 Attempting login for: $email');
      final response = await _apiService.post('/auth/login', data: {
        'email': email,
        'password': password,
      });

      if (response.statusCode == 200) {
        await _storage.write(key: 'access_token', value: response.data['access_token']);
        _user = User.fromJson(response.data['user']);
        _isAuthenticated = true;
        notifyListeners();
        print('✅ Login successful');
        return true;
      }
      print('❌ Login failed: Status ${response.statusCode}');
      return false;
    } catch (e) {
      print('❌ Login error: $e');
      return false;
    }
  }

  Future<bool> register(String name, String email, String password, {String? phone}) async {
    try {
      print('📝 Attempting registration for: $email');
      final response = await _apiService.post('/auth/register', data: {
        'name': name,
        'email': email,
        'password': password,
        'phone': phone,
      });

      if (response.statusCode == 201) {
        await _storage.write(key: 'access_token', value: response.data['access_token']);
        _user = User.fromJson(response.data['user']);
        _isAuthenticated = true;
        notifyListeners();
        print('✅ Registration successful');
        return true;
      }
      print('❌ Registration failed: Status ${response.statusCode}');
      return false;
    } catch (e) {
      print('❌ Registration error: $e');
      if (e is DioException && e.response != null) {
        print('   Error details: ${e.response?.data}');
      }
      return false;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
    _user = null;
    _isAuthenticated = false;
    notifyListeners();
  }

  Future<void> updateFcmToken(String token) async {
    try {
      await _apiService.post('/auth/update-fcm-token', data: {
        'fcm_token': token,
      });
    } catch (e) {
      // Silently fail
    }
  }
}
