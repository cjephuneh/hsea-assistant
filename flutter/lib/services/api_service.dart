import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:5001/api';
  final Dio _dio = Dio();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ApiService() {
    _dio.options.baseUrl = baseUrl;
    _dio.options.connectTimeout = const Duration(seconds: 30);
    _dio.options.receiveTimeout = const Duration(seconds: 30);
    
    // Add interceptor for auth token
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        print('🚨 Interceptor Error: ${error.message}');
        if (error.response != null) {
          print('   Response: ${error.response?.statusCode} - ${error.response?.data}');
        } else if (error.type == DioExceptionType.connectionTimeout) {
          print('   Connection timeout - is the backend running?');
        } else if (error.type == DioExceptionType.connectionError) {
          print('   Connection error - cannot reach backend at $baseUrl');
        }
        if (error.response?.statusCode == 401) {
          // Handle unauthorized - clear token and redirect to login
          _storage.delete(key: 'access_token');
        }
        return handler.next(error);
      },
    ));
  }

  Future<Response> get(String endpoint, {Map<String, dynamic>? queryParameters}) async {
    try {
      print('🌐 API GET: $baseUrl$endpoint');
      final response = await _dio.get(endpoint, queryParameters: queryParameters);
      print('✅ API Response: ${response.statusCode}');
      return response;
    } catch (e) {
      print('❌ API Error: $e');
      if (e is DioException) {
        print('   Status: ${e.response?.statusCode}');
        print('   Message: ${e.response?.data}');
      }
      rethrow;
    }
  }

  Future<Response> post(String endpoint, {dynamic data}) async {
    try {
      return await _dio.post(endpoint, data: data);
    } catch (e) {
      rethrow;
    }
  }

  Future<Response> put(String endpoint, {dynamic data}) async {
    try {
      return await _dio.put(endpoint, data: data);
    } catch (e) {
      rethrow;
    }
  }

  Future<Response> delete(String endpoint) async {
    try {
      return await _dio.delete(endpoint);
    } catch (e) {
      rethrow;
    }
  }
}
