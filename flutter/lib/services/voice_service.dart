import 'package:flutter/foundation.dart';
import 'api_service.dart';
import 'dart:convert';

class VoiceService {
  final ApiService _apiService = ApiService();

  Future<Map<String, dynamic>?> processVoiceCommand(String text) async {
    try {
      final response = await _apiService.post('/voice/command', data: {
        'text': text,
      });

      if (response.statusCode == 200 || response.statusCode == 201) {
        return response.data;
      }
    } catch (e) {
      debugPrint('Error processing voice command: $e');
    }
    return null;
  }

  Future<String?> transcribeAudio(String audioFilePath) async {
    try {
      // Note: This would need to be implemented with actual audio file upload
      // For now, this is a placeholder
      final response = await _apiService.post('/voice/transcribe', data: {
        'audio': audioFilePath,
      });

      if (response.statusCode == 200) {
        return response.data['text'];
      }
    } catch (e) {
      debugPrint('Error transcribing audio: $e');
    }
    return null;
  }
}
