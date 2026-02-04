import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../services/api_service.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  final ApiService _apiService = ApiService();
  Map<String, dynamic>? _taskCompletionData;
  Map<String, dynamic>? _userActivityData;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadReports();
  }

  Future<void> _loadReports() async {
    setState(() => _isLoading = true);
    try {
      final completionResponse = await _apiService.get('/reports/task-completion');
      final activityResponse = await _apiService.get('/reports/user-activity');

      if (completionResponse.statusCode == 200 && activityResponse.statusCode == 200) {
        setState(() {
          _taskCompletionData = completionResponse.data;
          _userActivityData = activityResponse.data;
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading reports: $e')),
        );
      }
    }
  }

  Future<void> _exportCSV() async {
    try {
      final response = await _apiService.get('/reports/export/csv');
      // Handle file download
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('CSV export started')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error exporting CSV: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reports'),
        actions: [
          IconButton(
            icon: const Icon(Icons.download),
            onPressed: _exportCSV,
            tooltip: 'Export CSV',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Task Completion Card
                  if (_taskCompletionData != null) ...[
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Task Completion',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 24),
                            Row(
                              children: [
                                Expanded(
                                  child: _buildStatCard(
                                    'Total',
                                    '${_taskCompletionData!['total_tasks']}',
                                    Icons.assignment,
                                    Colors.blue,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: _buildStatCard(
                                    'Completed',
                                    '${_taskCompletionData!['completed']}',
                                    Icons.check_circle,
                                    Colors.green,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Expanded(
                                  child: _buildStatCard(
                                    'In Progress',
                                    '${_taskCompletionData!['in_progress']}',
                                    Icons.hourglass_empty,
                                    Colors.orange,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: _buildStatCard(
                                    'Pending',
                                    '${_taskCompletionData!['pending']}',
                                    Icons.pending,
                                    Colors.grey,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 24),
                            SizedBox(
                              height: 200,
                              child: PieChart(
                                PieChartData(
                                  sections: [
                                    PieChartSectionData(
                                      value: _taskCompletionData!['completed'].toDouble(),
                                      color: Colors.green,
                                      title: '${_taskCompletionData!['completed']}',
                                      radius: 60,
                                    ),
                                    PieChartSectionData(
                                      value: _taskCompletionData!['in_progress'].toDouble(),
                                      color: Colors.orange,
                                      title: '${_taskCompletionData!['in_progress']}',
                                      radius: 60,
                                    ),
                                    PieChartSectionData(
                                      value: _taskCompletionData!['pending'].toDouble(),
                                      color: Colors.grey,
                                      title: '${_taskCompletionData!['pending']}',
                                      radius: 60,
                                    ),
                                  ],
                                  sectionsSpace: 2,
                                  centerSpaceRadius: 40,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // User Activity Card
                  if (_userActivityData != null)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'User Activity (Last ${_userActivityData!['period_days']} days)',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 24),
                            _buildStatCard(
                              'Tasks Created',
                              '${_userActivityData!['tasks_created']}',
                              Icons.add_task,
                              Colors.blue,
                            ),
                            const SizedBox(height: 12),
                            _buildStatCard(
                              'Tasks Completed',
                              '${_userActivityData!['tasks_completed']}',
                              Icons.check_circle_outline,
                              Colors.green,
                            ),
                            const SizedBox(height: 12),
                            _buildStatCard(
                              'Notifications',
                              '${_userActivityData!['notifications_received']}',
                              Icons.notifications,
                              Colors.orange,
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }
}
