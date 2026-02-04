import 'package:flutter/foundation.dart';
import '../models/task.dart';
import '../models/user.dart';
import 'api_service.dart';

class TaskService extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  List<Task> _tasks = [];
  bool _isLoading = false;

  List<Task> get tasks => _tasks;
  bool get isLoading => _isLoading;

  Future<void> fetchTasks({String? status, String? search}) async {
    _isLoading = true;
    notifyListeners();

    try {
      final response = await _apiService.get('/tasks', queryParameters: {
        if (status != null) 'status': status,
        if (search != null) 'search': search,
      });

      if (response.statusCode == 200) {
        _tasks = (response.data as List)
            .map((json) => Task.fromJson(json))
            .toList();
      }
    } catch (e) {
      debugPrint('Error fetching tasks: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Task?> createTask({
    required String title,
    required int assigneeId,
    String? description,
    String? priority,
    String? category,
    DateTime? dueDate,
  }) async {
    try {
      final response = await _apiService.post('/tasks', data: {
        'title': title,
        'assignee_id': assigneeId,
        'description': description,
        'priority': priority,
        'category': category,
        'due_date': dueDate?.toIso8601String(),
      });

      if (response.statusCode == 201) {
        final task = Task.fromJson(response.data);
        _tasks.insert(0, task);
        notifyListeners();
        return task;
      }
    } catch (e) {
      debugPrint('Error creating task: $e');
    }
    return null;
  }

  Future<bool> updateTask(int taskId, Map<String, dynamic> updates) async {
    try {
      final response = await _apiService.put('/tasks/$taskId', data: updates);

      if (response.statusCode == 200) {
        await fetchTasks();
        return true;
      }
    } catch (e) {
      debugPrint('Error updating task: $e');
    }
    return false;
  }

  Future<bool> deleteTask(int taskId) async {
    try {
      final response = await _apiService.delete('/tasks/$taskId');

      if (response.statusCode == 200) {
        _tasks.removeWhere((task) => task.id == taskId);
        notifyListeners();
        return true;
      }
    } catch (e) {
      debugPrint('Error deleting task: $e');
    }
    return false;
  }

  Future<List<User>> getUsers() async {
    try {
      final response = await _apiService.get('/tasks/users');
      if (response.statusCode == 200) {
        return (response.data as List)
            .map((json) => User.fromJson(json))
            .toList();
      }
    } catch (e) {
      debugPrint('Error fetching users: $e');
    }
    return [];
  }
}
