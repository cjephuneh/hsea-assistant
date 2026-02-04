import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../models/task.dart';
import '../../services/task_service.dart';
import '../../services/api_service.dart';
import '../../widgets/comment_widget.dart';
import '../../widgets/activity_feed_widget.dart';

class TaskDetailEnhancedScreen extends StatefulWidget {
  final int taskId;

  const TaskDetailEnhancedScreen({super.key, required this.taskId});

  @override
  State<TaskDetailEnhancedScreen> createState() => _TaskDetailEnhancedScreenState();
}

class _TaskDetailEnhancedScreenState extends State<TaskDetailEnhancedScreen> {
  final ApiService _apiService = ApiService();
  Task? _task;
  List<dynamic> _comments = [];
  List<dynamic> _activities = [];
  bool _isLoading = true;
  int _selectedTab = 0; // 0: Details, 1: Comments, 2: Activity

  @override
  void initState() {
    super.initState();
    _loadTask();
  }

  Future<void> _loadTask() async {
    setState(() => _isLoading = true);
    try {
      final taskResponse = await _apiService.get('/tasks/${widget.taskId}');
      final commentsResponse = await _apiService.get('/tasks/${widget.taskId}/comments');
      final activitiesResponse = await _apiService.get('/tasks/${widget.taskId}/activities');

      if (taskResponse.statusCode == 200) {
        setState(() {
          _task = Task.fromJson(taskResponse.data);
          _comments = commentsResponse.data ?? [];
          _activities = activitiesResponse.data ?? [];
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

  Future<void> _addComment(String content) async {
    try {
      final response = await _apiService.post('/tasks/${widget.taskId}/comments', data: {
        'content': content,
      });

      if (response.statusCode == 201) {
        _loadTask();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error adding comment: $e')),
        );
      }
    }
  }

  Future<void> _shareTask() async {
    try {
      final response = await _apiService.post('/tasks/${widget.taskId}/share', data: {
        'share_type': 'public',
      });

      if (response.statusCode == 200 && mounted) {
        final shareUrl = response.data['share_url'];
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Task Shared'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Task is now publicly accessible. Share this link:'),
                const SizedBox(height: 8),
                SelectableText(
                  shareUrl ?? '',
                  style: const TextStyle(fontSize: 12),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Close'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error sharing task: $e')),
        );
      }
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
            icon: const Icon(Icons.share),
            onPressed: _shareTask,
            tooltip: 'Share task',
          ),
        ],
      ),
      body: Column(
        children: [
          // Tab Bar
          Container(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              border: Border(
                bottom: BorderSide(color: Colors.grey.shade300),
              ),
            ),
            child: Row(
              children: [
                _buildTab(0, 'Details', Icons.info_outline),
                _buildTab(1, 'Comments', Icons.comment_outlined),
                _buildTab(2, 'Activity', Icons.history),
              ],
            ),
          ),
          
          // Content
          Expanded(
            child: IndexedStack(
              index: _selectedTab,
              children: [
                _buildDetailsTab(),
                _buildCommentsTab(),
                _buildActivityTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTab(int index, String label, IconData icon) {
    final isSelected = _selectedTab == index;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _selectedTab = index),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16.0),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: isSelected
                    ? Theme.of(context).colorScheme.primary
                    : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 20,
                color: isSelected
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey[600],
              ),
              const SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  color: isSelected
                      ? Theme.of(context).colorScheme.primary
                      : Colors.grey[600],
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _task!.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
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
          _buildInfoRow(Icons.person_outline, 'Assigned to', _task!.assignee.name),
          _buildInfoRow(Icons.person_add_outlined, 'Created by', _task!.createdBy.name),
          if (_task!.dueDate != null)
            _buildInfoRow(
              Icons.calendar_today,
              'Due date',
              DateFormat('MMM dd, yyyy').format(_task!.dueDate!),
            ),
          const SizedBox(height: 24),
          Row(
            children: [
              _buildStatusChip(_task!.status),
              const SizedBox(width: 8),
              _buildPriorityChip(_task!.priority),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCommentsTab() {
    return Column(
      children: [
        Expanded(
          child: _comments.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.comment_outlined, size: 64, color: Colors.grey[400]),
                      const SizedBox(height: 16),
                      Text(
                        'No comments yet',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16.0),
                  itemCount: _comments.length,
                  itemBuilder: (context, index) {
                    final comment = _comments[index];
                    return CommentWidget(comment: comment);
                  },
                ),
        ),
        Container(
          padding: const EdgeInsets.all(16.0),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            border: Border(
              top: BorderSide(color: Colors.grey.shade300),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: const InputDecoration(
                    hintText: 'Add a comment...',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  ),
                  onSubmitted: (value) {
                    if (value.isNotEmpty) {
                      _addComment(value);
                    }
                  },
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.send),
                onPressed: () {
                  // Handle send
                },
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActivityTab() {
    return _activities.isEmpty
        ? Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.history, size: 64, color: Colors.grey[400]),
                const SizedBox(height: 16),
                Text(
                  'No activity yet',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          )
        : ListView.builder(
            padding: const EdgeInsets.all(16.0),
            itemCount: _activities.length,
            itemBuilder: (context, index) {
              final activity = _activities[index];
              return ActivityFeedWidget(activity: activity);
            },
          );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Row(
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
      ),
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
