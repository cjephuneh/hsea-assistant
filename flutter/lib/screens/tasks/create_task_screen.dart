import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../models/task.dart';
import '../../models/user.dart';
import '../../services/task_service.dart';

class CreateTaskScreen extends StatefulWidget {
  final Task? task;

  const CreateTaskScreen({super.key, this.task});

  @override
  State<CreateTaskScreen> createState() => _CreateTaskScreenState();
}

class _CreateTaskScreenState extends State<CreateTaskScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _categoryController = TextEditingController();
  
  User? _selectedAssignee;
  TaskPriority _selectedPriority = TaskPriority.medium;
  DateTime? _selectedDueDate;
  List<User> _users = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    if (widget.task != null) {
      _titleController.text = widget.task!.title;
      _descriptionController.text = widget.task!.description ?? '';
      _categoryController.text = widget.task!.category ?? '';
      _selectedAssignee = widget.task!.assignee;
      _selectedPriority = widget.task!.priority;
      _selectedDueDate = widget.task!.dueDate;
    }
    _loadUsers();
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _categoryController.dispose();
    super.dispose();
  }

  Future<void> _loadUsers() async {
    final taskService = Provider.of<TaskService>(context, listen: false);
    final users = await taskService.getUsers();
    setState(() => _users = users);
  }

  Future<void> _selectDueDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDueDate ?? DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() => _selectedDueDate = picked);
    }
  }

  Future<void> _saveTask() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedAssignee == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select an assignee')),
      );
      return;
    }

    setState(() => _isLoading = true);

    final taskService = Provider.of<TaskService>(context, listen: false);
    
    if (widget.task != null) {
      // Update existing task
      final success = await taskService.updateTask(widget.task!.id, {
        'title': _titleController.text,
        'description': _descriptionController.text,
        'assignee_id': _selectedAssignee!.id,
        'priority': _selectedPriority.name,
        'category': _categoryController.text.isEmpty ? null : _categoryController.text,
        'due_date': _selectedDueDate?.toIso8601String(),
      });

      if (success && mounted) {
        Navigator.pop(context);
      }
    } else {
      // Create new task
      final task = await taskService.createTask(
        title: _titleController.text,
        assigneeId: _selectedAssignee!.id,
        description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
        priority: _selectedPriority.name,
        category: _categoryController.text.isEmpty ? null : _categoryController.text,
        dueDate: _selectedDueDate,
      );

      if (task != null && mounted) {
        Navigator.pop(context);
      }
    }

    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.task == null ? 'Create Task' : 'Edit Task'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16.0),
          children: [
            TextFormField(
              controller: _titleController,
              decoration: const InputDecoration(
                labelText: 'Title *',
                hintText: 'Enter task title',
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter a title';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description',
                hintText: 'Enter task description',
              ),
              maxLines: 4,
            ),
            const SizedBox(height: 16),
            
            // Assignee Dropdown
            DropdownButtonFormField<User>(
              value: _selectedAssignee,
              decoration: const InputDecoration(
                labelText: 'Assign to *',
              ),
              items: _users.map((user) {
                return DropdownMenuItem<User>(
                  value: user,
                  child: Text(user.name),
                );
              }).toList(),
              onChanged: (user) {
                setState(() => _selectedAssignee = user);
              },
              validator: (value) {
                if (value == null) {
                  return 'Please select an assignee';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            
            // Priority Dropdown
            DropdownButtonFormField<TaskPriority>(
              value: _selectedPriority,
              decoration: const InputDecoration(
                labelText: 'Priority',
              ),
              items: TaskPriority.values.map((priority) {
                return DropdownMenuItem<TaskPriority>(
                  value: priority,
                  child: Text(priority.name.toUpperCase()),
                );
              }).toList(),
              onChanged: (priority) {
                setState(() => _selectedPriority = priority!);
              },
            ),
            const SizedBox(height: 16),
            
            // Category
            TextFormField(
              controller: _categoryController,
              decoration: const InputDecoration(
                labelText: 'Category',
                hintText: 'Enter category',
              ),
            ),
            const SizedBox(height: 16),
            
            // Due Date
            InkWell(
              onTap: _selectDueDate,
              child: InputDecorator(
                decoration: const InputDecoration(
                  labelText: 'Due Date',
                  suffixIcon: Icon(Icons.calendar_today),
                ),
                child: Text(
                  _selectedDueDate != null
                      ? DateFormat('MMM dd, yyyy').format(_selectedDueDate!)
                      : 'Select due date',
                ),
              ),
            ),
            const SizedBox(height: 32),
            
            ElevatedButton(
              onPressed: _isLoading ? null : _saveTask,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _isLoading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(widget.task == null ? 'Create Task' : 'Update Task'),
            ),
          ],
        ),
      ),
    );
  }
}
