import 'user.dart';

enum TaskStatus { pending, inProgress, completed, cancelled }
enum TaskPriority { low, medium, high, urgent }

class Task {
  final int id;
  final String title;
  final String? description;
  final User assignee;
  final User createdBy;
  final TaskStatus status;
  final TaskPriority priority;
  final String? category;
  final DateTime? dueDate;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int commentsCount;

  Task({
    required this.id,
    required this.title,
    this.description,
    required this.assignee,
    required this.createdBy,
    required this.status,
    required this.priority,
    this.category,
    this.dueDate,
    required this.createdAt,
    required this.updatedAt,
    this.commentsCount = 0,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json['id'],
      title: json['title'],
      description: json['description'],
      assignee: User.fromJson(json['assignee']),
      createdBy: User.fromJson(json['created_by']),
      status: TaskStatus.values.firstWhere(
        (e) => e.name.toLowerCase() == json['status'].toLowerCase().replaceAll('_', ''),
        orElse: () => TaskStatus.pending,
      ),
      priority: TaskPriority.values.firstWhere(
        (e) => e.name.toLowerCase() == json['priority'].toLowerCase(),
        orElse: () => TaskPriority.medium,
      ),
      category: json['category'],
      dueDate: json['due_date'] != null ? DateTime.parse(json['due_date']) : null,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      commentsCount: json['comments_count'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'assignee_id': assignee.id,
      'status': status.name,
      'priority': priority.name,
      'category': category,
      'due_date': dueDate?.toIso8601String(),
    };
  }
}
