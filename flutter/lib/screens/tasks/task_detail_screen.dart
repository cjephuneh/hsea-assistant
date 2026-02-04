import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../models/task.dart';
import '../../services/task_service.dart';
import '../../services/api_service.dart';
import 'create_task_screen.dart';

class TaskDetailScreen extends StatefulWidget {
  final int taskId;

  const TaskDetailScreen({super.key, required this.taskId});

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  Task? _task;
  bool _isLoading = true;
  final ApiService _apiService = ApiService();

  @override
  void initState() {
    super.initState();
    _loadTask();
  }

  Future<void> _loadTask() async {
    try {
      final response = await _apiService.get('/tasks/${widget.taskId}');
      if (response.statusCode == 200) {
        setState(() {
          _task = Task.fromJson(response.data);
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading task: $e')),
        );
      }
    }
  }

  Future<void> _updateStatus(TaskStatus newStatus) async {
    final taskService = Provider.of<TaskService>(context, listen: false);
    final success = await taskService.updateTask(widget.taskId, {
      'status': newStatus.name,
    });

    if (success && mounted) {
      _loadTask();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Task updated successfully')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Task Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_task == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Task Details')),
        body: const Center(child: Text('Task not found')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Task Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () async {
              await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => CreateTaskScreen(task: _task),
                ),
              );
              _loadTask();
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title
            Text(
              _task!.title,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            // Status and Priority
            Row(
              children: [
                _buildStatusChip(_task!.status),
                const SizedBox(width: 8),
                _buildPriorityChip(_task!.priority),
              ],
            ),
            const SizedBox(height: 24),
            
            // Description
            if (_task!.description != null && _task!.description!.isNotEmpty) ...[
              Text(
                'Description',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _task!.description!,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 24),
            ],
            
            // Assignee
            _buildInfoRow(
              icon: Icons.person_outline,
              label: 'Assigned to',
              value: _task!.assignee.name,
            ),
            const SizedBox(height: 12),
            
            // Created by
            _buildInfoRow(
              icon: Icons.person_add_outlined,
              label: 'Created by',
              value: _task!.createdBy.name,
            ),
            const SizedBox(height: 12),
            
            // Due date
            if (_task!.dueDate != null)
              _buildInfoRow(
                icon: Icons.calendar_today,
                label: 'Due date',
                value: DateFormat('MMM dd, yyyy').format(_task!.dueDate!),
              ),
            const SizedBox(height: 24),
            
            // Status Actions
            Text(
              'Update Status',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (_task!.status != TaskStatus.pending)
                  ActionChip(
                    label: const Text('Mark as Pending'),
                    onPressed: () => _updateStatus(TaskStatus.pending),
                  ),
                if (_task!.status != TaskStatus.inProgress)
                  ActionChip(
                    label: const Text('Mark as In Progress'),
                    onPressed: () => _updateStatus(TaskStatus.inProgress),
                  ),
                if (_task!.status != TaskStatus.completed)
                  ActionChip(
                    label: const Text('Mark as Completed'),
                    onPressed: () => _updateStatus(TaskStatus.completed),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow({required IconData icon, required String label, required String value}) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Colors.grey[600]),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Colors.grey[600],
          ),
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildStatusChip(TaskStatus status) {
    Color color;
    switch (status) {
      case TaskStatus.completed:
        color = Colors.green;
        break;
      case TaskStatus.inProgress:
        color = Colors.blue;
        break;
      case TaskStatus.pending:
        color = Colors.grey;
        break;
      case TaskStatus.cancelled:
        color = Colors.red;
        break;
    }
    return Chip(
      label: Text(status.name.toUpperCase().replaceAll('_', ' ')),
      backgroundColor: color.withOpacity(0.1),
      labelStyle: TextStyle(color: color, fontWeight: FontWeight.w600),
    );
  }

  Widget _buildPriorityChip(TaskPriority priority) {
    Color color;
    switch (priority) {
      case TaskPriority.urgent:
        color = Colors.red;
        break;
      case TaskPriority.high:
        color = Colors.orange;
        break;
      case TaskPriority.medium:
        color = Colors.blue;
        break;
      case TaskPriority.low:
        color = Colors.green;
        break;
    }
    return Chip(
      label: Text(priority.name.toUpperCase()),
      backgroundColor: color.withOpacity(0.1),
      labelStyle: TextStyle(color: color, fontWeight: FontWeight.w600),
    );
  }
}
