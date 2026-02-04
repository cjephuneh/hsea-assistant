import 'package:flutter/foundation.dart';
import 'api_service.dart';
import 'auth_service.dart';

class NotificationService extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  int _unreadCount = 0;

  int get unreadCount => _unreadCount;

  Future<void> initialize(AuthService authService) async {
    // Firebase Messaging is optional - app works without it
    // To enable push notifications:
    // 1. Add GoogleService-Info.plist to ios/Runner/
    // 2. Uncomment Firebase code below
    // 3. Add import: import 'package:firebase_messaging/firebase_messaging.dart';
    
    debugPrint('Push notifications disabled - Firebase not configured');
    _loadUnreadCount();
    
    /* Uncomment when Firebase is configured:
    try {
      final firebaseMessaging = FirebaseMessaging.instance;
      
      NotificationSettings settings = await firebaseMessaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      if (settings.authorizationStatus == AuthorizationStatus.authorized) {
        String? token = await firebaseMessaging.getToken();
        if (token != null && authService.isAuthenticated) {
          await authService.updateFcmToken(token);
        }

        firebaseMessaging.onTokenRefresh.listen((newToken) {
          if (authService.isAuthenticated) {
            authService.updateFcmToken(newToken);
          }
        });

        FirebaseMessaging.onMessage.listen((RemoteMessage message) {
          debugPrint('Foreground message: ${message.notification?.title}');
        });

        FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
          debugPrint('Message opened: ${message.notification?.title}');
        });

        RemoteMessage? initialMessage = await firebaseMessaging.getInitialMessage();
        if (initialMessage != null) {
          debugPrint('App opened from notification: ${initialMessage.notification?.title}');
        }
      }
    } catch (e) {
      debugPrint('Firebase not configured: $e');
    }
    */
  }

  Future<void> _loadUnreadCount() async {
    try {
      final response = await _apiService.get('/notifications/unread-count');
      if (response.statusCode == 200) {
        _unreadCount = response.data['count'];
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error loading unread count: $e');
    }
  }

  Future<void> refreshUnreadCount() async {
    await _loadUnreadCount();
  }
}
